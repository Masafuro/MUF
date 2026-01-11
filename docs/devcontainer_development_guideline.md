# Devcontainer開発ガイドライン

## 1. 概要

このプロジェクトでは、VS Codeの.devcontainer環境を用いて開発を行うことができます。これにより、統一された開発環境が提供され、プロジェクトの開発を効率的に行えるようになります。

## 2. .devcontainerディレクトリの構成

プロジェクトルートディレクトリの`.devcontainer`ディレクトリには、開発環境の設定が含まれています。

### 2.1 .devcontainer/devcontainer.json

開発環境の設定ファイルです。以下の特徴を持っています：

- **開発環境名**: "MUF Full Project Development"
- **Docker Composeファイル**: メインのdocker-compose.ymlと、.devcontainer/docker-compose.extend.ymlを使用
- **サービス**: "muf-dev"サービスを使用
- **ワークスペース**: "/workspaces/MUF"ディレクトリがワークスペースとして設定
- **機能**: Dockerの機能を追加（docker-outside-of-docker）
- **環境変数**:
  - COMPOSE_FILE: "docker-compose.yml:.devcontainer/docker-compose.extend.yml"
  - PYTHONPATH: "/workspaces/MUF"
  - LOCAL_WORKSPACE_FOLDER: "${localWorkspaceFolder}"
- **拡張機能**:
  - Python拡張機能
  - Docker拡張機能
- **設定**:
  - Pythonの分析設定で"/workspaces/MUF"を追加
  - リモートユーザーをrootに設定

## 3. 開発環境の利点

- VS Codeでの統合開発環境
- Dockerコンテナベースの開発環境
- Pythonの開発環境が整備済み
- Dockerの操作が可能
- プロジェクトのPythonパスが適切に設定

## 4. 開発環境の設定手順

1. VS Codeを開く
2. プロジェクトディレクトリを開く
3. VS Codeのコマンドパレットを開く（Ctrl+Shift+P）
4. 「Dev Containers: Open Folder in Container」を選択
5. プロジェクトディレクトリを選択
6. 開発環境が自動的に構築される

## 5. 開発環境の特徴

### 5.1 Python環境
- Pythonパスが"/workspaces/MUF"に設定
- Pythonの開発拡張機能がインストール済み
- Pythonの分析設定が適切に設定

### 5.2 Docker環境
- Dockerの機能が追加（docker-outside-of-docker）
- Docker Composeが使用可能
- Dockerコンテナベースの開発環境

### 5.3 開発ツール
- VS Code拡張機能がインストール済み
  - Python拡張機能
  - Docker拡張機能
- Gitの設定が適切に設定

## 6. 開発環境の使い方

### 6.1 開発環境の起動
開発環境は、プロジェクトルートディレクトリの`.devcontainer`ディレクトリで定義されています。VS Codeでプロジェクトを開くと、自動的に開発環境が構築されます。

### 6.2 開発環境の利用
開発環境が構築された後、以下の機能が利用できます：
- Pythonの開発環境
- Dockerの操作
- VS Codeの拡張機能
- Gitの操作

## 7. 開発環境の利点

1. **統一された開発環境**: すべての開発者が同じ環境で開発できる
2. **効率的な開発**: 開発環境が自動的に構築されるため、手間が少ない
3. **環境の再現性**: 開発環境が再現可能で、トラブルシューティングが容易
4. **開発の標準化**: 開発環境が標準化され、プロジェクトの品質が向上

## 8. 注意事項

- 開発環境の構築には時間がかかる場合があります
- 開発環境の設定はプロジェクトの要件に合わせて調整してください
- 開発環境の設定は、プロジェクトの変更に応じて更新する必要があります
