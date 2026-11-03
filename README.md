# Zoom Meeting Creator

Zoom API（Server-to-Server OAuth）を使って、指定したユーザーをホストとする**即時会議**を作成する Python スクリプトです。

## 機能

- `.env` から Zoom の認証情報とホストのメールアドレスを読み込みます。
- `account_credentials` 方式でアクセストークンを取得します。
- `POST /v2/users/{userId}/meetings` で、`ZOOM_HOST_EMAIL` のユーザーをホストとする即時会議（`type=1`）を作成します。
- 待機室を有効にし、ホストより先の参加を禁止します。
- API から返された **会議ID・パスコード・参加URL** を表示します（返されなかった値はその旨を表示し、値を作りません）。
- エラー時は HTTP ステータスと Zoom のエラーコード／メッセージだけを表示し、認証情報やアクセストークンは出力しません。

## 前提条件

- Windows 10 / 11
- Python 3.9 以上
- Zoom Marketplace で作成・有効化済みの **Server-to-Server OAuth アプリ**
  - スコープ: `meeting:write:meeting:admin`
- ホストにするユーザーが、同じ Zoom アカウントに所属していること

## ファイル構成

| ファイル | 内容 |
| --- | --- |
| `main.py` | メインプログラム |
| `requirements.txt` | 必要な Python パッケージ |
| `.env.example` | 環境変数のサンプル（ダミー値） |
| `.gitignore` | `.env` などを Git の管理対象から除外 |
| `README.md` | このファイル |

## セットアップ（Windows PowerShell）

以下はすべてプロジェクトのフォルダで実行します。

### 1. 仮想環境を作成して有効化する

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

「このシステムではスクリプトの実行が無効になっている」というエラーが出た場合は、次のコマンドで現在のユーザーだけ実行を許可してから、もう一度有効化してください。

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 2. パッケージをインストールする

```powershell
pip install -r requirements.txt
```

### 3. `.env` を作成する

```powershell
Copy-Item .env.example .env
notepad .env
```

メモ帳が開いたら、Zoom Marketplace のアプリ画面（App Credentials）に表示されている値に書き換えて保存します。

```env
ZOOM_ACCOUNT_ID=実際のAccount ID
ZOOM_CLIENT_ID=実際のClient ID
ZOOM_CLIENT_SECRET=実際のClient Secret
ZOOM_HOST_EMAIL=ホストにするユーザーのメールアドレス
```

> `.env` は `.gitignore` に含まれているため、Git にはコミットされません。`.env` の内容を他人に見せたり、スクリーンショットに写したりしないよう注意してください。

## 実行

```powershell
python main.py
```

### 成功時の表示例

```text
Zoom会議を作成しました。
  会議ID   : （APIが返した会議ID）
  パスコード: （APIが返したパスコード）
  参加URL  : （APIが返した参加URL）
  待機室    : 有効
  ホスト前参加: 禁止
```

パスコードがアカウント設定で無効になっている場合など、API が値を返さなかった項目は `(APIから返されませんでした)` と表示されます。

### エラー時の表示例

```text
エラー: アクセストークンの取得に失敗しました: HTTP 400 (code: invalid_client, message: Invalid client_id or client_secret)
```

| 主な原因 | 確認すること |
| --- | --- |
| `.env` の項目が未設定 | `.env` がプロジェクト直下にあり、ダミー値が残っていないか |
| トークン取得で HTTP 400 / 401 | Account ID・Client ID・Client Secret が正しいか、アプリが有効化されているか |
| 会議作成で HTTP 400 / 404 | `ZOOM_HOST_EMAIL` が同じアカウント内の有効なユーザーか |
| 会議作成で HTTP 401 / 403 | スコープ `meeting:write:meeting:admin` が付与されているか |
| 会議作成で HTTP 429 | API のレート制限。時間をおいて再実行 |

## 補足

- Server-to-Server OAuth のトークンは特定のユーザーに紐づかないため、`/users/me/meetings` ではなく `/users/{メールアドレス}/meetings` を使っています。
- アクセストークンの有効期限は 1 時間です。このスクリプトは実行のたびに新しいトークンを取得します。
- ホスト用の開始URL（`start_url`）はホスト権限を持つため、画面には表示していません。
