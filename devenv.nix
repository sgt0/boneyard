{
  pkgs,
  lib,
  config,
  inputs,
  ...
}: {
  languages.python = {
    enable = true;
    version = "3.13";
    uv = {
      enable = true;
      sync = {
        enable = true;
        allExtras = true;
        allGroups = true;
      };
    };
  };

  git-hooks.hooks = {
    alejandra.enable = true;
    ruff.enable = true;
    ruff-format.enable = true;
  };
}
