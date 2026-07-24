# 统一解析 omni-dsdd 共享层根目录。
# 前提：omni-reverse 与 omni-dsdd 安装在同一 marketplace 下且目录并列。
# 用法：$dsdd = Resolve-DsddRoot

function Resolve-DsddRoot {
  $pr = $env:CLAUDE_PLUGIN_ROOT
  $cand = if ($pr) { Join-Path $pr "..\omni-dsdd" } else { Join-Path $PSScriptRoot "..\..\omni-dsdd" }
  $resolved = (Resolve-Path $cand -ErrorAction SilentlyContinue).Path
  if (-not $resolved `
      -or -not (Test-Path (Join-Path $resolved "scripts")) `
      -or -not (Test-Path (Join-Path $resolved "omni-infra"))) {
    throw "未找到共享插件 omni-dsdd，需与 omni-reverse 同 marketplace 并列安装。"
  }
  return $resolved
}

# 直接执行时打印路径
if ($MyInvocation.InvocationName -ne '.') { Resolve-DsddRoot }
