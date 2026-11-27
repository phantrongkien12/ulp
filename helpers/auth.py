import os
import json
from telethon import events
from config import OWNER_ID, ADMIN_ID, STORAGE_CHANNEL_ID

ADMINS_FILE = "admins.json"


def _load_admins() -> set[int]:
    admins = {int(OWNER_ID)}
    if ADMIN_ID:
        admins.add(int(ADMIN_ID))

    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                admins.update(int(uid) for uid in data.get("admins", []))
        except Exception:
            pass
    return admins


def _save_admins(admins: set[int]):
    admins.add(int(OWNER_ID))
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump({"admins": sorted(list(admins))}, f, indent=2)


def is_owner(user_id: int) -> bool:
    return int(user_id) == int(OWNER_ID)


def is_authorized(user_id: int) -> bool:
    return int(user_id) in _load_admins()


def setup_access_control(client):
    @client.on(events.NewMessage())
    async def global_message_guard(event):
        if STORAGE_CHANNEL_ID and event.chat_id == int(STORAGE_CHANNEL_ID):
            return

        sender_id = event.sender_id
        if not sender_id or not is_authorized(sender_id):
            raise events.StopPropagation

    @client.on(events.CallbackQuery())
    async def global_callback_guard(event):
        if not is_authorized(event.sender_id):
            await event.answer("⛔ Bạn không có quyền sử dụng bot này.", alert=True)
            raise events.StopPropagation

    @client.on(events.NewMessage(pattern=r"^[!/\.]addadmin(?:\s+(\d+))?$"))
    async def cmd_add_admin(event):
        if not is_owner(event.sender_id):
            return

        target_id = None
        if event.pattern_match.group(1):
            target_id = int(event.pattern_match.group(1))
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            target_id = reply_msg.sender_id

        if not target_id:
            await event.reply("⚠️ Cách dùng: `/addadmin <user_id>` hoặc reply tin nhắn của người đó.")
            raise events.StopPropagation

        admins = _load_admins()
        admins.add(target_id)
        _save_admins(admins)
        await event.reply(f"✅ Đã cấp quyền Admin cho ID: `{target_id}`")
        raise events.StopPropagation

    @client.on(events.NewMessage(pattern=r"^[!/\.]deladmin(?:\s+(\d+))?$"))
    async def cmd_del_admin(event):
        if not is_owner(event.sender_id):
            return

        target_id = None
        if event.pattern_match.group(1):
            target_id = int(event.pattern_match.group(1))
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            target_id = reply_msg.sender_id

        if not target_id:
            await event.reply("⚠️ Cách dùng: `/deladmin <user_id>` hoặc reply tin nhắn của người đó.")
            raise events.StopPropagation

        if target_id == int(OWNER_ID):
            await event.reply("⛔ Không thể xóa quyền của Owner.")
            raise events.StopPropagation

        admins = _load_admins()
        if target_id in admins:
            admins.remove(target_id)
            _save_admins(admins)
            await event.reply(f"🗑️ Đã thu hồi quyền Admin của ID: `{target_id}`")
        else:
            await event.reply(f"ℹ️ ID `{target_id}` không nằm trong danh sách Admin.")
        raise events.StopPropagation

    @client.on(events.NewMessage(pattern=r"^[!/\.]admins$"))
    async def cmd_list_admins(event):
        if not is_owner(event.sender_id):
            return

        admins = _load_admins()
        lines = [f"👑 **Owner:** `{OWNER_ID}`\n🛡 **Danh sách được phép dùng bot:**"]
        for uid in sorted(admins):
            tag = " (Owner)" if uid == int(OWNER_ID) else ""
            lines.append(f"- `{uid}`{tag}")
        await event.reply("\n".join(lines))
        raise events.StopPropagation
