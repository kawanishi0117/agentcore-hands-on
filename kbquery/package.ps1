# kbquery/package.ps1
# Lambda関数用のZIPファイルを作成するスクリプト（Windows PowerShell用）
# 作成したZIPファイルをAWSコンソールから手動でアップロードしてください

Write-Host "📦 Lambda関数のパッケージングを開始します..." -ForegroundColor Green

# 1. 一時ディレクトリを作成
$tempDir = "$env:TEMP\lambda-package-$(Get-Date -Format 'yyyyMMddHHmmss')"
Write-Host "📁 パッケージング用ディレクトリ: $tempDir" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

# 2. 依存関係をインストール
Write-Host "📥 依存関係をインストール中..." -ForegroundColor Cyan
pip install -r requirements.txt -t $tempDir --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 依存関係のインストールに失敗しました" -ForegroundColor Red
    Remove-Item $tempDir -Recurse -Force
    exit 1
}

# 3. Pythonファイルをコピー
Write-Host "📄 Pythonファイルをコピー中..." -ForegroundColor Cyan
Copy-Item "lambda_function.py" $tempDir
Copy-Item "kb_config.py" $tempDir

# 4. ZIPファイルを作成
Write-Host "🗜️  ZIPファイルを作成中..." -ForegroundColor Cyan
$zipPath = Join-Path $PSScriptRoot "function.zip"

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

# PowerShellでZIP作成
Add-Type -Assembly System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($tempDir, $zipPath)

# 5. 一時ディレクトリを削除
Write-Host "🧹 一時ファイルをクリーンアップ中..." -ForegroundColor Cyan
Remove-Item $tempDir -Recurse -Force

# 完了メッセージ
Write-Host "`n✅ パッケージング完了！" -ForegroundColor Green
Write-Host "📦 ZIPファイル: $zipPath" -ForegroundColor Cyan
Write-Host "`n次のステップ:" -ForegroundColor Yellow
Write-Host "1. AWSコンソールでLambda関数を開く" -ForegroundColor White
Write-Host "2. [コード] タブで [アップロード元] → [.zipファイル] を選択" -ForegroundColor White
Write-Host "3. function.zip をアップロード" -ForegroundColor White
Write-Host "4. [保存] をクリック" -ForegroundColor White
