#!/usr/bin/env pwsh
# 测试并行处理脚本
# 测试get-next-batches.ps1和update-batches-status.ps1脚本的功能

# 创建测试环境
function Create-TestEnvironment {
    # 创建临时目录
    $testDir = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath ([System.IO.Path]::GetRandomFileName())
    $cacheDir = Join-Path -Path $testDir -ChildPath ".cache/omni-reverse/interfaces"
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null

    # 创建测试批次映射文件
    $batchMapping = @{
        total_batches = 3
        batch_size = 3
        batches = @(
            @{batch_number = 1; batch_file = "batch-details-1.json"; status = "pending"}
            @{batch_number = 2; batch_file = "batch-details-2.json"; status = "pending"}
            @{batch_number = 3; batch_file = "batch-details-3.json"; status = "pending"}
        )
    }
    $batchMapping | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path -Path $cacheDir -ChildPath "batch-mapping.json") -Encoding UTF8

    # 创建测试批次详细文件
    for ($i = 1; $i -le 3; $i++) {
        $batchDetails = @{
            batch_number = $i
            files = @("/test/file${i}_1.java", "/test/file${i}_2.java")
            estimated_tokens = 10000
            complexity_score = 5.0
            status = "pending"
        }
        $batchDetails | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path -Path $cacheDir -ChildPath "batch-details-$i.json") -Encoding UTF8
    }

    # 创建批次状态文件
    $batchStatus = @{
        version = "1.1"
        stage = "interface_scanning"
        total_items = 6
        batch_size = 20
        total_batches = 3
        processed_batches = 0
        current_batch = 0
        failed_batches = 0
        start_time = ""
        last_update = ""
        status = "initialized"
        batch_mappings = @(
            @{batch_number = 1; batch_file = "batch-details-1.json"; status = "pending"; estimated_tokens = 10000}
            @{batch_number = 2; batch_file = "batch-details-2.json"; status = "pending"; estimated_tokens = 10000}
            @{batch_number = 3; batch_file = "batch-details-3.json"; status = "pending"; estimated_tokens = 10000}
        )
    }
    $batchStatus | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path -Path $cacheDir -ChildPath "interface_scanning-batch-status.json") -Encoding UTF8

    return $testDir
}

# 测试获取下一个批次脚本
function Test-GetNextBatches {
    param([string]$TestDir)

    Write-Host "测试 get-next-batches.ps1 脚本..."

    $scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "get-next-batches.ps1"
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

        Write-Host "获取到 $($output.Count) 个批次:"
        foreach ($batch in $output) {
            Write-Host "  批次 $($batch.batch_number): $($batch.status)"
        }

        if ($output.Count -gt 0) {
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

# 测试批量更新批次状态脚本
function Test-UpdateBatchesStatus {
    param([string]$TestDir)

    Write-Host "测试 update-batches-status.ps1 脚本..."

    $scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "update-batches-status.ps1"
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
    Write-Host "开始测试并行处理脚本..."

    # 创建测试环境
    $testDir = Create-TestEnvironment
    Write-Host "已创建测试环境: $testDir"

    $success1 = $false
    $success2 = $false

    try {
        # 测试获取批次脚本
        $success1 = Test-GetNextBatches -TestDir $testDir

        Write-Host ""

        # 测试更新批次状态脚本
        $success2 = Test-UpdateBatchesStatus -TestDir $testDir

        if ($success1 -and $success2) {
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