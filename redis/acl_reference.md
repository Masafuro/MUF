# MUF System: Redis ACL 管理ガイド

このドキュメントは、MUFシステムにおけるRedisのアクセス制御（ACL）の切り替え手順と設定内容を管理するためのものです。実際の users.acl ファイルには構文の制限でコメントを記述できないため、設定変更の際はこのガイドを参照してください。

## 1. 環境別の ACL 設定内容

以下のいずれかの設定内容をコピーして、ホスト側の users.acl ファイルに貼り付けてください。その際、余計な空白行やスペースが含まれないように注意してください。

### A. デバッグ環境用（デフォルトユーザー有効）
開発時や初期テストで使用する設定です。nopass を指定することで、デフォルトユーザーによる全操作を許可します。

user default on nopass ~* &* +@all
user muf_app on >SecurePass789 ~muf:* &* +@all

### B. 実行・本番環境用（デフォルトユーザー無効）
セキュリティを強化し、特定の認証情報を持つユニットのみが接続できる設定です。

user default off
user muf_app on >SecurePass789 ~muf:* &* +@all

## 2. 設定の反映と確認の手順

設定を反映させるためには、ファイルの更新後にコンテナの再起動が必要です。

**手順1：ファイルの編集**
ホスト側の ./users.acl ファイルを上記のいずれかの内容で書き換えて保存します。

**手順2：コンテナの強制再起動**
以下のコマンドを実行し、ファイルをマウントし直してRedisを再構築します。
docker compose up -d --force-recreate muf-redis

**手順3：設定内容の検証**
コンテナ内で cat コマンドを実行し、意図した通りの権限行が表示されるか確認します。
docker compose exec muf-redis cat /data/users.acl

## 3. 動作テスト用のコマンド

ACLが正しく機能しているかを確認するために、以下の redis-cli コマンドを利用してください。

**ユーザーリストの確認**
docker compose exec muf-redis redis-cli ACL LIST

**muf_app ユーザーでの認証テスト**
docker compose exec muf-redis redis-cli -u redis://muf_app:SecurePass789@localhost:6379 ping

**デフォルトユーザーの拒否テスト（off設定時）**
docker compose exec muf-redis redis-cli ping
この際、(error) NOAUTH Authentication required. というエラーが出れば正常に制限されています。

## 4. 注意事項：空ディレクトリのトラブルについて

もし users.acl という名前の空のディレクトリがホスト側に作成されてしまった場合は、そのままではファイルの読み込みができません。その場合は一度 docker compose down を実行した上で、該当するディレクトリを削除してから、改めてテキストファイルとして users.acl を作成し直してください。