"""Zoom Server-to-Server OAuth を使ってテスト用の即時会議を作成するスクリプト。

処理の流れ:
    1. .env から認証情報とホストのメールアドレスを読み込む
    2. account_credentials 方式でアクセストークンを取得する
    3. POST /v2/users/{userId}/meetings で即時会議 (type=1) を作成する
    4. API が返した会議ID・パスコード・参加URLを表示する

セキュリティ上の方針:
    - クライアントシークレットやアクセストークンは一切画面に出力しない
    - エラー時は HTTP ステータスと Zoom のエラーコード/メッセージのみ表示する
    - ホスト用の start_url (ホスト権限付きURL) は表示しない
"""

import os
import sys
from urllib.parse import quote

import requests
from dotenv import load_dotenv

ZOOM_OAUTH_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE = "https://api.zoom.us/v2"
REQUEST_TIMEOUT_SECONDS = 15

REQUIRED_ENV_VARS = (
    "ZOOM_ACCOUNT_ID",
    "ZOOM_CLIENT_ID",
    "ZOOM_CLIENT_SECRET",
    "ZOOM_HOST_EMAIL",
)


class ZoomError(Exception):
    """利用者に表示しても安全なメッセージだけを持つ例外。"""


def load_config() -> dict:
    """.env を読み込み、必要な値がすべて揃っているか確認する。"""
    load_dotenv()

    config = {}
    missing = []
    for name in REQUIRED_ENV_VARS:
        value = os.getenv(name, "").strip()
        if not value or value.startswith("your_"):
            missing.append(name)
        config[name] = value

    if missing:
        # 値そのものは出さず、変数名だけを伝える
        raise ZoomError(
            ".env の次の項目が未設定、またはダミー値のままです: " + ", ".join(missing)
        )
    return config


def describe_http_error(response: requests.Response) -> str:
    """HTTP エラーを、機密情報を含まない短い文章に変換する。"""
    detail = ""
    try:
        body = response.json()
        # OAuth エンドポイントは error / reason、API は code / message を返す
        code = body.get("code") or body.get("error")
        message = body.get("message") or body.get("reason")
        if code or message:
            detail = f" (code: {code}, message: {message})"
    except ValueError:
        pass  # JSON でない場合は本文を表示しない
    return f"HTTP {response.status_code}{detail}"


def get_access_token(account_id: str, client_id: str, client_secret: str) -> str:
    """Server-to-Server OAuth (account_credentials) でアクセストークンを取得する。"""
    try:
        response = requests.post(
            ZOOM_OAUTH_URL,
            params={"grant_type": "account_credentials", "account_id": account_id},
            auth=(client_id, client_secret),  # Basic 認証ヘッダーは requests が生成
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # 例外メッセージには URL (account_id を含む) が入るため、種類だけを表示
        raise ZoomError(f"トークン取得時に通信エラーが発生しました: {type(exc).__name__}") from None

    if not response.ok:
        raise ZoomError("アクセストークンの取得に失敗しました: " + describe_http_error(response))

    token = response.json().get("access_token")
    if not token:
        raise ZoomError("トークン応答に access_token が含まれていませんでした。")
    return token


def create_instant_meeting(access_token: str, host_email: str) -> dict:
    """指定ユーザーをホストとして即時会議 (type=1) を作成する。"""
    # Server-to-Server OAuth では /users/me ではなく、ユーザーIDまたはメールを指定する
    url = f"{ZOOM_API_BASE}/users/{quote(host_email, safe='')}/meetings"
    payload = {
        "topic": "AIスクール課題 テスト会議",
        "type": 1,  # 1 = 即時会議
        "settings": {
            "waiting_room": True,       # 待機室を有効化
            "join_before_host": False,  # ホストより先の参加を禁止
        },
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ZoomError(f"会議作成時に通信エラーが発生しました: {type(exc).__name__}") from None

    if not response.ok:
        raise ZoomError("会議の作成に失敗しました: " + describe_http_error(response))

    return response.json()


def print_meeting_info(meeting: dict) -> None:
    """API が実際に返した値だけを表示する（無い値は捏造しない）。"""
    not_returned = "(APIから返されませんでした)"

    print("Zoom会議を作成しました。")
    print(f"  会議ID   : {meeting.get('id', not_returned)}")
    print(f"  パスコード: {meeting.get('password') or not_returned}")
    print(f"  参加URL  : {meeting.get('join_url', not_returned)}")

    settings = meeting.get("settings", {})
    if "waiting_room" in settings:
        print(f"  待機室    : {'有効' if settings['waiting_room'] else '無効'}")
    if "join_before_host" in settings:
        print(f"  ホスト前参加: {'許可' if settings['join_before_host'] else '禁止'}")


def main() -> int:
    try:
        config = load_config()
        token = get_access_token(
            config["ZOOM_ACCOUNT_ID"],
            config["ZOOM_CLIENT_ID"],
            config["ZOOM_CLIENT_SECRET"],
        )
        meeting = create_instant_meeting(token, config["ZOOM_HOST_EMAIL"])
    except ZoomError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    print_meeting_info(meeting)
    return 0


if __name__ == "__main__":
    sys.exit(main())
