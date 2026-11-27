import os
import json
import asyncio
from telethon import events
from telethon.tl.types import DocumentAttributeFilename, InputMessagePinned
from config import STORAGE_CHANNEL_ID

DATA_DIR = "data"
INDEX_HEADER = "#ULP_DB_INDEX\n"
_sync_lock = asyncio.Lock()


def _get_doc_info(message) -> tuple[str | None, int]:
    if not message or not message.document:
        return None, 0
    fname = None
    for attr in message.document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            fname = attr.file_name
            break
    return fname, message.document.size


async def _get_pinned_index(client) -> tuple[int | None, dict]:
    if not STORAGE_CHANNEL_ID:
        return None, {}

    try:
        pinned_msg = await client.get_messages(STORAGE_CHANNEL_ID, ids=InputMessagePinned())
        if pinned_msg and pinned_msg.text and pinned_msg.text.startswith(INDEX_HEADER):
            raw_json = pinned_msg.text[len(INDEX_HEADER):].strip()
            return pinned_msg.id, json.loads(raw_json)
    except Exception as e:
        print(f"[PoolSync] Lỗi đọc Pinned Index: {e}")

    return None, {}


async def _save_pinned_index(client, pin_msg_id: int | None, index_data: dict):
    if not STORAGE_CHANNEL_ID:
        return

    payload = INDEX_HEADER + json.dumps(index_data, ensure_ascii=False, separators=(",", ":"))
    try:
        if pin_msg_id:
            await client.edit_message(STORAGE_CHANNEL_ID, pin_msg_id, payload)
        else:
            sent = await client.send_message(STORAGE_CHANNEL_ID, payload)
            await client.pin_message(STORAGE_CHANNEL_ID, sent.id, notify=False)
    except Exception as e:
        print(f"[PoolSync] Lỗi lưu Pinned Index: {e}")


async def sync_from_channel_on_startup(client):
    if not STORAGE_CHANNEL_ID:
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    pin_id, index_data = await _get_pinned_index(client)
    if not index_data:
        print("[PoolSync] Pool đang trống, chưa có file nào được index.")
        return

    msg_ids = [int(mid) for mid in index_data.keys()]
    print(f"[PoolSync] Tìm thấy {len(msg_ids)} file trong Pool. Bắt đầu đồng bộ về VPS...")

    downloaded = 0
    for i in range(0, len(msg_ids), 50):
        batch_ids = msg_ids[i:i + 50]
        messages = await client.get_messages(STORAGE_CHANNEL_ID, ids=batch_ids)
        for msg in messages:
            if not msg or not msg.document:
                continue

            meta = index_data.get(str(msg.id), {})
            fname, fsize = _get_doc_info(msg)
            fname = meta.get("name") or fname or f"pool_{msg.id}.txt"
            dest_path = os.path.join(DATA_DIR, fname)

            if os.path.exists(dest_path) and os.path.getsize(dest_path) == fsize:
                continue

            print(f"[PoolSync] Đang tải: {fname} ({fsize / (1024*1024):.2f} MB)...")
            await client.download_media(msg, file=dest_path)
            downloaded += 1

    print(f"[PoolSync] Hoàn tất! Đã tải mới {downloaded}/{len(msg_ids)} file.")


def register_channel_watcher(client):
    if not STORAGE_CHANNEL_ID:
        return

    @client.on(events.NewMessage(chats=STORAGE_CHANNEL_ID))
    async def on_pool_file_added(event):
        fname, fsize = _get_doc_info(event.message)
        if not fname or not fname.lower().endswith(".txt"):
            return

        async with _sync_lock:
            os.makedirs(DATA_DIR, exist_ok=True)
            pin_id, index_data = await _get_pinned_index(client)

            for existing_mid, meta in index_data.items():
                if meta.get("name") == fname and meta.get("size") == fsize:
                    await event.reply(f"⚠️ Bỏ qua `{fname}` (đã tồn tại trong Pool ở msg `{existing_mid}`).")
                    return

            save_name = fname
            dest_path = os.path.join(DATA_DIR, save_name)
            if os.path.exists(dest_path):
                save_name = f"{event.message.id}_{fname}"
                dest_path = os.path.join(DATA_DIR, save_name)

            status = await event.reply(f"⏳ Đang nạp `{save_name}` ({fsize / (1024*1024):.2f} MB) vào VPS...")
            await client.download_media(event.message, file=dest_path)

            index_data[str(event.message.id)] = {"name": save_name, "size": fsize}
            await _save_pinned_index(client, pin_id, index_data)

            await status.edit(f"✅ Đã nạp `{save_name}` | Tổng Pool: **{len(index_data)}** file.")
