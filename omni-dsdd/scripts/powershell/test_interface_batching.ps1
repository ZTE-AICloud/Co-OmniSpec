#!/usr/bin/env pwsh
# 测试接口批处理功能脚本 (PowerShell版本)
# 验证interface-analyzer子Agent和批处理相关脚本的功能

param(
    [switch]$Help
)

# 显示帮助信息
function Show-Help {
    @"
测试接口批处理功能脚本 (PowerShell版本)
验证interface-analyzer子Agent和批处理相关脚本的功能

使用方法:
    .\test_interface_batching.ps1

参数:
    -Help: 显示此帮助信息
"@
}

# 如果请求帮助，显示帮助信息并退出
if ($Help) {
    Show-Help
    exit 0
}

# 创建测试环境
function Create-TestEnvironment {
    # 创建临时目录
    $testDir = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath ([System.IO.Path]::GetRandomFileName())
    $cacheDir = Join-Path -Path $testDir -ChildPath ".cache/reverse/interfaces"
    $outputDir = Join-Path -Path $testDir -ChildPath "omni-doc/specs/interfaces"
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

    # 创建测试接口清单文件
    $interfaceList = @{
        version = "1.0"
        generated_at = "2026-01-15T10:30:00Z"
        total_interfaces = 8
        interfaces = @(
            @{
                interface_id = "API-001"
                name = "getUserInfo"
                interface_type = "RESTful API"
                source_file = "/test/controllers/user.controller.js"
                path_method = "/api/users/{id} GET"
                processing_status = "pending"
            },
            @{
                interface_id = "API-002"
                name = "createUser"
                interface_type = "RESTful API"
                source_file = "/test/controllers/user.controller.js"
                path_method = "/api/users POST"
                processing_status = "pending"
            },
            @{
                interface_id = "API-003"
                name = "updateUser"
                interface_type = "RESTful API"
                source_file = "/test/controllers/user.controller.js"
                path_method = "/api/users/{id} PUT"
                processing_status = "pending"
            },
            @{
                interface_id = "API-004"
                name = "deleteUser"
                interface_type = "RESTful API"
                source_file = "/test/controllers/user.controller.js"
                path_method = "/api/users/{id} DELETE"
                processing_status = "pending"
            },
            @{
                interface_id = "API-005"
                name = "listUsers"
                interface_type = "RESTful API"
                source_file = "/test/controllers/user.controller.js"
                path_method = "/api/users GET"
                processing_status = "pending"
            },
            @{
                interface_id = "API-006"
                name = "getUserProfile"
                interface_type = "RESTful API"
                source_file = "/test/controllers/profile.controller.js"
                path_method = "/api/profile/{id} GET"
                processing_status = "pending"
            },
            @{
                interface_id = "API-007"
                name = "updateProfile"
                interface_type = "RESTful API"
                source_file = "/test/controllers/profile.controller.js"
                path_method = "/api/profile/{id} PUT"
                processing_status = "pending"
            },
            @{
                interface_id = "API-008"
                name = "deleteProfile"
                interface_type = "RESTful API"
                source_file = "/test/controllers/profile.controller.js"
                path_method = "/api/profile/{id} DELETE"
                processing_status = "pending"
            }
        )
    }
    $interfaceList | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path -Path $cacheDir -ChildPath "interface-list.json") -Encoding UTF8

    # 创建模板文件
    $detailTemplate = @"
# 接口文档：{{interface_name}}

## 基本信息
- **接口ID**: {{interface_id}}
- **接口名称**: {{interface_name}}
- **接口类型**: {{interface_type}}
- **所属文件**: {{source_file}}

## 接口描述
{{#description}}
{{description}}
{{/description}}
{{^description}}
（该接口暂无详细描述）
{{/description}}
"@
    $detailTemplate | Set-Content -Path (Join-Path -Path $testDir -ChildPath ".omni-infra/templates/reverse-interface-detail-template.md") -Encoding UTF8

    $inventoryTemplate = @"
# 接口清单

## 概述
- 总接口数: {{total_interfaces}}
- 生成时间: {{generated_at}}

## 接口列表
{{#interfaces}}
- [{{interface_id}}]({{interface_id}}_{{name}}.md) - {{name}} ({{interface_type}})
{{/interfaces}}
"@
    $inventoryTemplate | Set-Content -Path (Join-Path -Path $testDir -ChildPath ".omni-infra/templates/reverse-interface-inventory-template.md") -Encoding UTF8

    return $testDir
}

# 测试创建接口批次脚本
function Test-CreateInterfaceBatches {
    param([string]$TestDir)

    Write-Host "测试 create_interface_batches.py 脚本..."

    $scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "create_interface_batches.py"
    if (-not (Test-Path -Path $scriptPath -PathType Leaf)) {
        Write-Error "错误: 脚本文件不存在 $scriptPath"
        return $false
    }

    # 执行脚本
    try {
        $output = & python $scriptPath $TestDir
        if ($LASTEXITCODE -ne 0) {
            Write-Error "脚本执行失败: $output"
            return $false
        }

        # 验证生成的文件
        $cacheDir = Join-Path -Path $TestDir -ChildPath ".cache/reverse/interfaces"
        if (-not (Test-Path -Path (Join-Path -Path $cacheDir -ChildPath "interface-batch-mapping.json") -PathType Leaf)) {
            Write-Error "错误: 批次映射文件未生成"
            return $false
        }

        if (-not (Test-Path -Path (Join-Path -Path $cacheDir -ChildPath "interface_detail-batch-status.json") -PathType Leaf)) {
            Write-Error "错误: 批次状态文件未生成"
            return $false
        }

        # 检查批次详细文件
        $batchMapping = Get-Content -Path (Join-Path -Path $cacheDir -ChildPath "interface-batch-mapping.json") -Raw | ConvertFrom-Json
        $batchCount = $batchMapping.total_batches
        for ($i = 1; $i -le $batchCount; $i++) {
            if (-not (Test-Path -Path (Join-Path -Path $cacheDir -ChildPath "interface-batch-details-$i.json") -PathType Leaf)) {
                Write-Error "错误: 批次详细文件 interface-batch-details-$i.json 未生成"
                return $false
            }
        }

        Write-Host "✅ 批次创建测试通过"
        Write-Host "生成了 $batchCount 个批次"
        return $true
    } catch {
        Write-Error "测试过程中发生错误: $_"
        return $false
    }
}

# 测试获取接口批次脚本
function Test-GetNextInterfaceBatches {
    param([string]$TestDir)

    Write-Host "测试 Get-NextInterfaceBatches.ps1 脚本..."

    $scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "Get-NextInterfaceBatches.ps1"
    if (-not (Test-Path -Path $scriptPath -PathType Leaf)) {
        Write-Error "错误: 脚本文件不存在 $scriptPath"
        return $false
    }

    # 执行脚本
    try {
        $output = & $scriptPath -RepoRoot $TestDir -BatchCount 2
        if ($LASTEXITCODE -ne 0) {
            Write-Error "脚本执行失败: $output"
            return $false
        }

        # 解析输出
        $batches = $output | ConvertFrom-Json
        $batchCount = $batches.Count

        Write-Host "获取到 $batchCount 个批次:"
        foreach ($batch in $batches) {
            Write-Host "  批次 $($batch.batch_number): $($batch.status)"
        }

        if ($batchCount -gt 0) {
            Write-Host "✅ 获取批次测试通过"
            return $true
        } else {
            Write-Host "❌ 获取批次测试失败"
            return $false
        }
    } catch {
        Write-Error "测试过程中发生错误: $_"
        return $false
    }
}

# 测试更新接口批次状态脚本
function Test-UpdateInterfaceBatchesStatus {
    param([string]$TestDir)

    Write-Host "测试 Update-InterfaceBatchesStatus.ps1 脚本..."

    $scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "Update-InterfaceBatchesStatus.ps1"
    if (-not (Test-Path -Path $scriptPath -PathType Leaf)) {
        Write-Error "错误: 脚本文件不存在 $scriptPath"
        return $false
    }

    # 准备更新数据
    $batchUpdates = @(
        @{batch_number = 1; status = "processing"}
        @{batch_number = 2; status = "processing"}
    ) | ConvertTo-Json -Compress

    # 执行脚本
    try {
        $output = & $scriptPath -RepoRoot $TestDir -BatchUpdates $batchUpdates
        if ($LASTEXITCODE -ne 0) {
            Write-Error "脚本执行失败 (退出码: $LASTEXITCODE): $output"
            return $false
        }

        # 解析输出
        Write-Host "更新结果: $output"

        # 验证更新是否成功
        $result = $output | ConvertFrom-Json
        if ($result.success -gt 0) {
            Write-Host "✅ 批次状态更新测试通过"
            return $true
        } else {
            Write-Host "❌ 批次状态更新测试失败"
            return $false
        }
    } catch {
        Write-Error "测试过程中发生错误: $_"
        return $false
    }
}

# 清理测试环境
function Cleanup-TestEnvironment {
    param([string]$TestDir)

    if (Test-Path -Path $TestDir -PathType Container) {
        Remove-Item -Path $TestDir -Recurse -Force
        Write-Host "已清理测试环境: $TestDir"
    }
}

# 主函数
function Main {
    Write-Host "开始测试接口批处理功能..."

    # 创建测试环境
    $testDir = Create-TestEnvironment
    Write-Host "已创建测试环境: $testDir"

    $success1 = $false
    $success2 = $false
    $success3 = $false

    try {
        # 测试创建批次脚本
        $success1 = Test-CreateInterfaceBatches -TestDir $testDir

        Write-Host ""

        # 测试获取批次脚本
        $success2 = Test-GetNextInterfaceBatches -TestDir $testDir

        Write-Host ""

        # 测试更新批次状态脚本
        $success3 = Test-UpdateInterfaceBatchesStatus -TestDir $testDir

        if ($success1 -and $success2 -and $success3) {
            Write-Host ""
            Write-Host "🎉 所有测试通过!"
            return 0
        } else {
            Write-Host ""
            Write-Host "💥 部分测试失败!"
            return 1
        }
    } finally {
        # 清理测试环境
        Cleanup-TestEnvironment -TestDir $testDir
    }
}

# 执行主函数
Main