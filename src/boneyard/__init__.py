from __future__ import annotations

from collections.abc import Callable, Iterator
from statistics import fmean
from typing import Any, Literal, Self, override

from ass import Style
from ass.data import Color
from jetpytools import (
    CustomIntEnum,
    CustomRuntimeError,
    Sentinel,
    SentinelT,
    SingleOrArr,
)
from pydantic import BaseModel
from muxtools import default_style_args, edit_style
from vsdenoise import MVToolsPreset, Prefilter, bm3d, mc_degrain, nl_means
from vsdenoise.blockmatch import BM3D
from vsdenoise.nlm import NLMeans
from vstools import (
    ChromaLocation,
    VSObjectMeta,
    clip_async_render,
    clip_data_gather,
    core,
    depth,
    get_prop,
    get_w,
    merge_clip_props,
    replace_ranges,
    vs,
)
from vstools import Keyframes as JetpackKeyframes
from vstools.functions.timecodes import SceneBasedDynamicCache

__all__ = (
    "LOFT_MOON_FIRA_DEFAULT",
    "LOFT_MOON_FIRA_ALT",
    "LOFT_MOON_SIGNS",
    "LOFT_MOON_FIRA_PRESET",
    "denoise",
    "SceneBasedCambi",
    "SceneChangeMode",
    "Keyframes",
    "VSModelMeta",
)


LOFT_MOON_FIRA_DEFAULT = Style(
    name="Default",
    fontname="Fira Sans Medium",
    fontsize=69.0,
    outline=4.4,
    shadow=2.2,
    margin_l=275,
    margin_r=275,
    margin_v=60,
    **(
        default_style_args
        | {
            "bold": False,
            "secondary_color": Color(r=0x00, g=0x00, b=0x00, a=0x00),
            "outline_color": Color(r=0x1F, g=0x29, b=0x12, a=0x00),
            "back_color": Color(r=0x1F, g=0x29, b=0x12, a=0xA0),
        }
    ),
)

LOFT_MOON_FIRA_ALT = edit_style(
    LOFT_MOON_FIRA_DEFAULT,
    "Alt",
    outline_color=Color(r=0x4C, g=0x21, b=0x48, a=0x00),
    back_color=Color(r=0x4C, g=0x21, b=0x48, a=0xA0),
)

LOFT_MOON_SIGNS = Style(
    name="Signs",
    fontname="Fira Sans Medium",
    fontsize=80.0,
    outline=0.0,
    shadow=0.0,
    margin_l=0,
    margin_r=0,
    margin_v=0,
    **(
        default_style_args
        | {
            "bold": False,
            "alignment": 5,
            "secondary_color": Color(r=0xFF, g=0xFF, b=0xFF, a=0x00),
            "outline_color": Color(r=0x00, g=0x00, b=0x00, a=0x00),
            "back_color": Color(r=0x00, g=0x00, b=0x00, a=0x00),
        }
    ),
)

LOFT_MOON_FIRA_PRESET = [
    LOFT_MOON_FIRA_DEFAULT,
    LOFT_MOON_FIRA_ALT,
    LOFT_MOON_SIGNS,
]


def denoise(
    clip: vs.VideoNode,
    block_size: int = 64,
    limit: int | tuple[int | None, int | None] | None = None,
    refine: int = 3,
    sigma: SingleOrArr[float] = 0.7,
    sr: int = 2,
    strength: float = 0.2,
    thSAD: int | tuple[int, int] = 115,  # noqa: N803
    tr: int = 2,
) -> vs.VideoNode:
    """MVTools + BM3D + NLMeans denoise."""

    clip_16 = depth(clip, 16)
    clip_32 = depth(clip, 32)

    ref = mc_degrain(
        clip_16,
        prefilter=Prefilter.DFTTEST,
        preset=MVToolsPreset.HQ_SAD,
        blksize=block_size,
        thsad=thSAD,
        limit=limit,
        refine=refine,
    )
    ref = depth(ref, 32)

    denoised_luma = bm3d(
        clip_32, ref=ref, sigma=sigma, tr=tr, profile=BM3D.Profile.NORMAL, planes=0
    )
    denoised_luma = ChromaLocation.ensure_presence(
        denoised_luma, ChromaLocation.from_video(clip, strict=True)
    )

    return nl_means(
        denoised_luma,
        ref=ref,
        h=strength,
        tr=tr,
        a=sr,
        wmode=NLMeans.WeightMode.BISQUARE_HR,  # wmode=3
        planes=[1, 2],
    )


class SceneBasedCambi(SceneBasedDynamicCache):
    def __init__(
        self,
        clip: vs.VideoNode,
        keyframes: Keyframes | str,
        cache_size: int = 5,
    ) -> None:
        super().__init__(core.cambi.Cambi(clip), keyframes, cache_size)

    @override
    def get_clip(self, key: int) -> vs.VideoNode:
        frame_range = self.keyframes.scenes[key]
        cut = self.clip[frame_range.start : frame_range.stop]
        frames_cambis = clip_data_gather(
            cut, None, lambda _, f: get_prop(f, "CAMBI", float)
        )
        avg_cambi = fmean(frames_cambis)
        return self.clip.std.SetFrameProps(Scene_Avg_CAMBI=avg_cambi)


class SceneChangeMode(CustomIntEnum):
    """Enum for various scene change modes."""

    WWXD = 1
    """Get the scene changes using the vapoursynth-wwxd plugin."""

    SCXVID = 2
    """Get the scene changes using the vapoursynth-scxvid plugin."""

    WWXD_SCXVID_UNION = 3  # WWXD | SCXVID
    """Get every scene change detected by both wwxd or scxvid."""

    WWXD_SCXVID_INTERSECTION = 0  # WWXD & SCXVID
    """
    Only get the scene changes if both wwxd and scxvid mark a frame as being a
    scene change.
    """

    @property
    def is_WWXD(self) -> bool:  # noqa: N802
        """Check whether a mode that uses wwxd is used."""

        return self in (
            SceneChangeMode.WWXD,
            SceneChangeMode.WWXD_SCXVID_UNION,
            SceneChangeMode.WWXD_SCXVID_INTERSECTION,
        )

    @property
    def is_SCXVID(self) -> bool:  # noqa: N802
        """Check whether a mode that uses scxvid is used."""

        return self in (
            SceneChangeMode.SCXVID,
            SceneChangeMode.WWXD_SCXVID_UNION,
            SceneChangeMode.WWXD_SCXVID_INTERSECTION,
        )

    def ensure_presence(self, clip: vs.VideoNode) -> vs.VideoNode:
        """
        Ensures all the frame properties necessary for scene change detection
        are created.
        """

        stats_clip = list[vs.VideoNode]()

        if self.is_SCXVID:
            if not hasattr(vs.core, "scxvid"):
                raise CustomRuntimeError("Missing scxvid plugin.", self.ensure_presence)
            stats_clip.append(clip.scxvid.Scxvid())

        if self.is_WWXD:
            if not hasattr(vs.core, "wwxd"):
                raise CustomRuntimeError("Missing wwxd plugin.", self.ensure_presence)
            stats_clip.append(clip.wwxd.WWXD())

        keys = tuple(self.prop_keys)

        expr = " ".join([f"x.{k}" for k in keys]) + (" and" * (len(keys) - 1))

        blank = clip.std.BlankClip(1, 1, vs.GRAY8, keep=True)

        if len(stats_clip) > 1:
            return merge_clip_props(blank, *stats_clip).akarin.Expr(expr)

        return blank.std.CopyFrameProps(stats_clip[0]).akarin.Expr(expr)

    @property
    def prop_keys(self) -> Iterator[str]:
        if self.is_WWXD:
            yield "Scenechange"

        if self.is_SCXVID:
            yield "_SceneChangePrev"

    def lambda_cb(self) -> Callable[[int, vs.VideoFrame], SentinelT | int]:
        return lambda n, f: Sentinel.check(n, bool(f[0][0, 0]))

    def prepare_clip(
        self, clip: vs.VideoNode, height: int | Literal[False] = 360
    ) -> vs.VideoNode:
        """
        Prepare a clip for scene change metric calculations.

        The clip will always be resampled to YUV420 8bit if it's not already,
        as that's what the plugins support.

        Args:
            clip: Clip to process.
            height: Output height of the clip. Smaller frame sizes are faster to
                process, but may miss more scene changes or introduce more false
                positives. Width is automatically calculated. `False` means no
                resizing operation is performed. Default: 360.

        Returns:
            A prepared clip for performing scene change metric calculations on.
        """

        if height:
            clip = clip.resize.Bilinear(get_w(height, clip), height, vs.YUV420P8)
        elif not clip.format or (clip.format and clip.format.id != vs.YUV420P8):
            clip = clip.resize.Bilinear(format=vs.YUV420P8)

        return self.ensure_presence(clip)


class Keyframes(JetpackKeyframes):
    """
    Class representing keyframes, or scenechanges.

    They follow the convention of signaling the start of the new scene.
    """

    @classmethod
    @override
    def from_clip(
        cls,
        clip: vs.VideoNode,
        mode: SceneChangeMode = SceneChangeMode.SCXVID,
        height: int | Literal[False] = 360,
        **kwargs: Any,
    ) -> Self:
        mode = SceneChangeMode(mode)

        clip = mode.prepare_clip(clip, height)

        frames = clip_async_render(
            clip, None, "Detecting scene changes...", mode.lambda_cb(), **kwargs
        )

        return cls(Sentinel.filter(frames))

    def to_clip(
        self,
        clip: vs.VideoNode,
        *,
        prop_key: str = next(iter(SceneChangeMode.SCXVID.prop_keys)),
        scene_idx_prop: bool = False,
    ) -> vs.VideoNode:
        propset_clip = clip.std.SetFrameProp(prop_key, True)

        out = replace_ranges(clip, propset_clip, self)

        if not scene_idx_prop:
            return out

        def _add_scene_idx(n: int, f: vs.VideoFrame) -> vs.VideoFrame:
            f = f.copy()

            f.props._SceneIdx = self.scenes.indices[n]

            return f

        return out.std.ModifyFrame(out, _add_scene_idx)


class VSModelMeta(VSObjectMeta, type(BaseModel)):  # type: ignore[misc]
    """
    Metaclass for classes that are both pydantic models and objects bound to the
    lifecycle of a VapourSynth core.

    Usage:
        ```py
        class MyModel(BaseModel, VSObject, metaclass=VSModelMeta): ...
        ```
    """
