import sqlite3
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from datetime import datetime, timedelta
import hashlib
from command.sendLog import sendLog

async def sync(client):
    # 認証情報（credentials.json は GCP で取得したサービスアカウントキー）
    SERVICE_ACCOUNT_FILE = 'credentials.json'
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('calendar', 'v3', credentials=creds)

    CALENDAR_ID = 'e96b3471a18e7559f5c62878fe790ad9ce4746e46c130212a2e3614e607791d3@group.calendar.google.com'  # または特定のカレンダーID

    # SQLiteからデータ読み込み
    conn = sqlite3.connect('TASK.db')
    cursor = conn.cursor()
    cursor.execute("SELECT subject, month, day, hour, minute FROM task")
    tasks = cursor.fetchall()

    current_year = datetime.now().year

    # イベントIDを生成（Googleの仕様を考慮）
    def generate_event_id(subject, month, day, hour, minute):
                # 現在時刻も含めて毎回異なるIDを生成
        now = datetime.now().isoformat(timespec="microseconds")
        dt = datetime(current_year, month, day, hour, minute)
        timestamp = int(dt.timestamp())
        raw = f"{subject}-{timestamp}-{now}"
        hash_id = hashlib.md5(raw.encode()).hexdigest()[:16]
        return f"t{hash_id}"  # 英字から始まるようにする（Google仕様）

    existing_ids_in_db = set()

    # 各タスク処理
    for subject, month, day, hour, minute in tasks:
        try:
            # 型変換
            month = int(month)
            day = int(day)
            hour = int(hour)
            minute = int(minute)

            # イベントID生成
            event_id = generate_event_id(subject, month, day, hour, minute)
            existing_ids_in_db.add(event_id)

            # 修正後（1時間前から始まるイベント）
            end_dt = datetime(current_year, month, day, hour, minute)
            start_dt = end_dt - timedelta(hours=1)

            event = {
                "id": event_id,
                "summary": subject,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Tokyo"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Tokyo"},
            }

            # 既存イベントの取得
            try:
                existing_event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()

                # 内容に変更があるか判定
                needs_update = (
                    existing_event.get("summary") != subject or
                    existing_event["start"]["dateTime"] != start_dt.isoformat() or
                    existing_event["end"]["dateTime"] != end_dt.isoformat()
                )

                if needs_update:
                    existing_event["summary"] = subject
                    existing_event["start"]["dateTime"] = start_dt.isoformat()
                    existing_event["end"]["dateTime"] = end_dt.isoformat()
                    existing_event["start"]["timeZone"] = "Asia/Tokyo"
                    existing_event["end"]["timeZone"] = "Asia/Tokyo"

                    service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=existing_event).execute()
                    await sendLog(client,f"Updated: {subject}")
                else:
                    await sendLog(client,f"Skipped (no change): {subject}")

            except HttpError as e:
                if e.resp.status == 404:
                    try:
                        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
                        await sendLog(client,f"Added: {subject}")
                    except HttpError as insert_error:
                        await sendLog(client,f"Failed to insert event for '{subject}': {insert_error}")
                else:
                    await sendLog(client,f"Unhandled error for '{subject}' during GET: {e}")

        except Exception as ex:
            await sendLog(client,f"Error processing task '{subject}': {ex}")

    # カレンダーから不要なイベントを削除する
    page_token = None
    while True:
        events_result = service.events().list(calendarId=CALENDAR_ID, pageToken=page_token).execute()
        events = events_result.get('items', [])
        for event in events:
            event_id = event.get('id')
            if event_id and event_id.startswith('t') and event_id not in existing_ids_in_db:
                try:
                    service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
                    await sendLog(client,f"Deleted: {event.get('summary')} ({event_id})")
                except HttpError as e:
                    if e.resp.status == 410:
                        await sendLog(client,f"Event {event_id} was already deleted.")
                    else:
                        await sendLog(client,f"Error deleting event {event_id}: {e}")
        page_token = events_result.get('nextPageToken')
        if not page_token:
            break

    conn.close()