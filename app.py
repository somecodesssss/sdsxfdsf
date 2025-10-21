#!/usr/bin/env python3
# =============================================================================
# app.py — minimal AAA features only (Render-ready: only token in env)
# =============================================================================

import io, os, os.path as op, json, asyncio, random, datetime as dt, typing as t, urllib.parse, uuid, re
import discord
from discord import app_commands
from discord.ext import commands

# ========================== CONFIG ==========================
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]  # REQUIRED

GUILD_ID                 = "1270144230525763697"
EPHEMERAL                = True
DATA_PATH                = "bot_data.json"

# --- Logging / Admin ---
LOG_CHANNEL_ID           = "1418651467736420402"
ADMIN_ROLE_ID            = "1418651226865799228"

# --- Temp Voice Channels ---
TEMP_VC_HUB_ID           = "1418651399679381626"
TEMP_VC_CATEGORY_ID      = "1418651380834504765"

# --- Invite tracker ---
INVITE_TRACK_CHANNEL_ID  = "1418651401042530496"

# --- Tickets ---
TICKET_CATEGORY_ID       = "1418651387071561871"
TICKET_PANEL_CHANNEL_ID  = "1418651459502739577"

# --- Giveaways ---
GIVEAWAY_CHANNEL_ID      = "1418651444567081122"

# --- Levels ---
LEVEL_ANNOUNCE_CHANNEL_ID = "1418651426007158935"
ROLE_L10   = 1270164309602865315
ROLE_L15   = 1270164755927138384
ROLE_L20   = 1270164954154270731
ROLE_L25   = 1270165116712652860
ROLE_L50   = 1270165259004678165

# --- Counting game ---
COUNTING_CHANNEL_ID      = "1418651415596761232"

# --- Self roles panel ---
SELFROLES_CHANNEL_ID     = "1418651397414719610"

# --- Self roles groups and options ---
ORIGIN_PARENT            = 1418651296923254919
ORIGIN_OPTIONS = {
    "Antarctica": 1418651306100391956,
    "South America": 1418651304464744611,
    "North America": 1418651303818825918,
    "Eurasia": 1418651302506008667,
    "Europe": 1418651301616681020,
    "Australia": 1418651300555391147,
    "Asia": 1418651299418865826,
}

PLATFORM_PARENT          = 1418651313163731147
PLATFORM_OPTIONS = {
    "Mobile Phone": 1418651314098798692,
    "Computer": 1418651315185385632,
    "Playstation": 1418651316670169240,
    "Xbox": 1418651317534199929,
    "Nitendo": 1418651318356283412,
}

GENDER_PARENT            = 1418651291566997696
GENDER_OPTIONS = {
    "Male": 1418651293840576562,
    "Female": 1418651295031628061,
    "Transgender": 1418651295908106311,
}

ABOUT_PARENT             = 1418651286395683007
ABOUT_OPTIONS = {
    "12-14 Years Old": 1418651288899682404,
    "15-17 Years Old": 1418651289814044714,
    "18+ Years Old": 1418651291072073809,
}

# ========================= RUNTIME SETUP ====================
import io, os, os.path as op, json, asyncio, random, datetime as dt, typing as t, urllib.parse, uuid, re
import discord
from discord import app_commands
from discord.ext import commands

# --------------------------- helpers ------------------------
def _to_int(val: str) -> t.Optional[int]:
    try:
        return int(str(val or "").strip())
    except Exception:
        return None

TOKEN                        = (DISCORD_TOKEN or "").strip()
if not TOKEN:
    raise SystemExit("❌ DISCORD_TOKEN is empty")

GUILD_ID_INT                 = _to_int(GUILD_ID)
LOG_CHANNEL_ID_INT           = _to_int(LOG_CHANNEL_ID)
ADMIN_ROLE_ID_INT            = _to_int(ADMIN_ROLE_ID)
TEMP_VC_HUB_ID_INT           = _to_int(TEMP_VC_HUB_ID)
TEMP_VC_CATEGORY_ID_INT      = _to_int(TEMP_VC_CATEGORY_ID)
INVITE_TRACK_CHANNEL_ID_INT  = _to_int(INVITE_TRACK_CHANNEL_ID)
GIVEAWAY_CHANNEL_ID_INT      = _to_int(GIVEAWAY_CHANNEL_ID)
TICKET_CATEGORY_ID_INT       = _to_int(TICKET_CATEGORY_ID)
TICKET_PANEL_CHANNEL_ID_INT  = _to_int(TICKET_PANEL_CHANNEL_ID)
LEVEL_ANNOUNCE_CHANNEL_ID_INT= _to_int(LEVEL_ANNOUNCE_CHANNEL_ID)
COUNTING_CHANNEL_ID_INT      = _to_int(COUNTING_CHANNEL_ID)
SELFROLES_CHANNEL_ID_INT     = _to_int(SELFROLES_CHANNEL_ID)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)

def load_db() -> dict:
    d = {}
    if op.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
    d.setdefault("tempvc_owner", {})
    d.setdefault("invites", {})
    d.setdefault("gw_active", {})
    d.setdefault("tickets", {})
    d.setdefault("ticket_panel_msg_id", None)
    d.setdefault("selfroles_panel_msg_id", None)
    d.setdefault("xp", {})
    d.setdefault("xp_cooldowns", {})
    d.setdefault("counting", {})  # per-guild: {guild_id: {"last": 0, "last_user": 0}}
    return d

def save_db(db: dict) -> None:
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

DB = load_db()

# ========================= AAA EMBED CORE ===================
BRAND = {
    "primary": 0x5865F2,
    "ok": 0x2ECC71,
    "warn": 0xF1C40F,
    "err": 0xE74C3C,
    "info": 0x3498DB,
    "muted": 0x95A5A6,
}

def _log_channel(guild: discord.Guild) -> t.Optional[discord.TextChannel]:
    if LOG_CHANNEL_ID_INT:
        ch = guild.get_channel(LOG_CHANNEL_ID_INT)
        if isinstance(ch, discord.TextChannel):
            return ch
    return None

async def aaa_log(
    guild: t.Optional[discord.Guild],
    title: str,
    color: int,
    *,
    actor: t.Optional[discord.abc.User] = None,
    target: t.Optional[discord.abc.User] = None,
    fields: t.Optional[dict] = None,
    image: t.Optional[str] = None,
    thumbnail: t.Optional[str] = None,
    footer: t.Optional[str] = None,
    ref: t.Optional[str] = None,
) -> None:
    if guild is None:
        return
    ch = _log_channel(guild)
    if not ch:
        return

    e = discord.Embed(title=title, color=color, timestamp=dt.datetime.utcnow())
    if actor:
        e.add_field(name="Actor", value=f"{actor.mention}\n`{getattr(actor,'id','?')}`", inline=True)
        try:
            e.set_thumbnail(url=actor.display_avatar.url)
        except Exception:
            pass
    if target:
        e.add_field(name="Target", value=f"{target.mention}\n`{getattr(target,'id','?')}`", inline=True)
        try:
            e.set_image(url=target.display_avatar.url)
        except Exception:
            pass
    if fields:
        for k, v in fields.items():
            if v is None:
                continue
            s = str(v)
            e.add_field(name=k, value=(s[:1024] if len(s) > 1024 else s), inline=False)
    if image:
        e.set_image(url=image)
    if thumbnail:
        e.set_thumbnail(url=thumbnail)
    e.set_footer(text=(footer or "event"))
    try:
        await ch.send(content=(ref or None), embed=e)
    except Exception:
        pass

def is_admin(member: t.Union[discord.Member, discord.User]) -> bool:
    try:
        perms = getattr(member, "guild_permissions", None)
        if getattr(perms, "administrator", False):
            return True
    except Exception:
        pass
    try:
        if ADMIN_ROLE_ID_INT and getattr(member, "guild", None):
            role = member.guild.get_role(ADMIN_ROLE_ID_INT)
            if role and role in getattr(member, "roles", []):
                return True
    except Exception:
        pass
    return False


def admin_check():
    async def predicate(inter: discord.Interaction):
        if not isinstance(inter.user, discord.Member):
            raise app_commands.CheckFailure("Not in guild")
        if is_admin(inter.user):
            return True
        raise app_commands.CheckFailure("Insufficient permissions")
    return app_commands.check(predicate)

# ========================= MEDIA (AAA UI) ===================
async def _file_from_asset(asset: discord.Asset, base: str, quality: str) -> tuple[discord.File, str]:
    def _asset_is_animated(a: discord.Asset) -> bool:
        try:
            attr = getattr(a, "is_animated", None)
            if callable(attr):
                return bool(attr())
            if attr is not None:
                return bool(attr)
        except Exception:
            pass
        try:
            url = str(a.url)
        except Exception:
            url = str(a)
        name = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
        return name.endswith(".gif") or name.startswith("a_")
    is_anim = _asset_is_animated(asset)
    try:
        if is_anim:
            try: asset = asset.with_format("gif")
            except Exception: pass
        if quality == "max" or (quality == "auto" and is_anim):
            try: asset = asset.with_size(4096)
            except Exception: pass
    except Exception:
        pass
    try:
        final_url = str(asset.url)
    except Exception:
        final_url = ""
    data = await asset.read()
    safe = "".join(ch for ch in base if ch.isalnum() or ch in ("_", "-", "."))
    ext = ".png"
    try:
        path = urllib.parse.urlparse(final_url).path
        _, ext0 = os.path.splitext(path)
        if ext0:
            ext = ext0
    except Exception:
        pass
    return discord.File(io.BytesIO(data), filename=f"{safe}{ext}"), final_url

class MediaView(discord.ui.View):
    def __init__(self, resolver: t.Callable[[str], t.Awaitable[tuple[discord.File, str]]], *, initial_quality="auto"):
        super().__init__(timeout=180)
        self.resolver = resolver
        self.current_q = initial_quality
        self.add_item(self.QualitySelect(self))

    class QualitySelect(discord.ui.Select):
        def __init__(self, view: "MediaView"):
            opts = [
                discord.SelectOption(label="auto", description="animated->4096, static->original", value="auto"),
                discord.SelectOption(label="original", description="no resize", value="original"),
                discord.SelectOption(label="max", description="request 4096", value="max"),
            ]
            super().__init__(placeholder="Select quality", options=opts, min_values=1, max_values=1)
            self.mv = view

        async def callback(self, interaction: discord.Interaction):
            q = self.values[0]
            self.mv.current_q = q
            file, url = await self.mv.resolver(q)
            e = discord.Embed(title="Media", color=BRAND["primary"], timestamp=dt.datetime.utcnow())
            e.add_field(name="Quality", value=q, inline=True)
            e.add_field(name="CDN", value=f"`{url}`", inline=False)
            e.set_image(url=url)
            await interaction.response.edit_message(embed=e, attachments=[file], view=self.mv)
            # NOTE: intentionally NOT logging media-quality changes (requested)

class Media(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @app_commands.command(name="avatar", description="Download a member’s server avatar")
    @app_commands.describe(user="defaults to you", quality="auto|original|max")
    @app_commands.choices(quality=[
        app_commands.Choice(name="auto", value="auto"),
        app_commands.Choice(name="original", value="original"),
        app_commands.Choice(name="max", value="max"),
    ])
    async def avatar(self, inter: discord.Interaction, user: t.Optional[discord.Member] = None,
                     quality: app_commands.Choice[str] = None):
        member = user or inter.user
        q = quality.value if quality else "auto"
        asset = getattr(member, "guild_avatar", None) or member.display_avatar

        async def resolve(qv: str):
            return await _file_from_asset(asset, f"{member.name}_avatar_server", qv)

        file, url = await resolve(q)
        e = discord.Embed(title=f"Avatar • {member.display_name}", color=BRAND["primary"], timestamp=dt.datetime.utcnow())
        e.add_field(name="Quality", value=q, inline=True)
        e.add_field(name="CDN", value=f"`{url}`", inline=False)
        e.set_image(url=url)
        await inter.response.send_message(embed=e, file=file, ephemeral=EPHEMERAL, view=MediaView(resolve, initial_quality=q))
        if inter.guild:
            await aaa_log(inter.guild, "Avatar fetch", BRAND["info"], actor=inter.user, target=member, fields={"quality": q, "url": url})

    @app_commands.command(name="banner", description="Download a member’s server banner or global banner")
    @app_commands.describe(user="defaults to you", quality="auto|original|max")
    @app_commands.choices(quality=[
        app_commands.Choice(name="auto", value="auto"),
        app_commands.Choice(name="original", value="original"),
        app_commands.Choice(name="max", value="max"),
    ])
    async def banner(self, inter: discord.Interaction, user: t.Optional[discord.Member] = None,
                     quality: app_commands.Choice[str] = None):
        member = user or inter.user
        q = quality.value if quality else "auto"
        guild = inter.guild
        if guild is None:
            await inter.response.send_message("Use in a server", ephemeral=True)
            return

        async def resolve(qv: str):
            try:
                payload = await self.bot.http.get_member(guild.id, member.id)
                banner_hash = payload.get("banner")
                if banner_hash:
                    anim = str(banner_hash).startswith("a_")
                    ext = "gif" if anim else "png"
                    url = f"https://cdn.discordapp.com/guilds/{guild.id}/users/{member.id}/banners/{banner_hash}.{ext}"
                    if qv == "max" or (qv == "auto" and anim):
                        url += "?size=4096"
                    import aiohttp
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url) as r:
                            r.raise_for_status()
                            data = await r.read()
                    return discord.File(io.BytesIO(data), filename=f"{member.name}_banner_server.{ext}"), url
            except Exception:
                pass
            try:
                user_obj = await self.bot.fetch_user(member.id)
            except Exception:
                user_obj = None
            if user_obj and user_obj.banner:
                return await _file_from_asset(user_obj.banner, f"{member.name}_banner_global", qv)
            raise RuntimeError("No banner")

        try:
            file, url = await resolve(q)
        except Exception:
            await inter.response.send_message("No server or global banner", ephemeral=True)
            return

        e = discord.Embed(title=f"Banner • {member.display_name}", color=BRAND["primary"], timestamp=dt.datetime.utcnow())
        e.add_field(name="Quality", value=q, inline=True)
        e.add_field(name="CDN", value=f"`{url}`", inline=False)
        e.set_image(url=url)
        await inter.response.send_message(embed=e, file=file, ephemeral=EPHEMERAL, view=MediaView(resolve, initial_quality=q))
        await aaa_log(guild, "Banner fetch", BRAND["info"], actor=inter.user, target=member, fields={"quality": q, "url": url})

    @app_commands.command(name="server_icon", description="Download this server’s icon")
    @app_commands.describe(quality="auto|original|max")
    @app_commands.choices(quality=[
        app_commands.Choice(name="auto", value="auto"),
        app_commands.Choice(name="original", value="original"),
        app_commands.Choice(name="max", value="max"),
    ])
    async def server_icon(self, inter: discord.Interaction, quality: app_commands.Choice[str] = None):
        if not inter.guild:
            await inter.response.send_message("Use in a server", ephemeral=True)
            return
        guild = inter.guild
        if not guild.icon:
            await inter.response.send_message("No server icon", ephemeral=True)
            return
        q = quality.value if quality else "auto"

        async def resolve(qv: str):
            return await _file_from_asset(guild.icon, f"{guild.name}_icon", qv)

        file, url = await resolve(q)
        e = discord.Embed(title=f"Server Icon • {guild.name}", color=BRAND["primary"], timestamp=dt.datetime.utcnow())
        e.add_field(name="Quality", value=q, inline=True)
        e.add_field(name="CDN", value=f"`{url}`", inline=False)
        e.set_image(url=url)
        await inter.response.send_message(embed=e, file=file, ephemeral=EPHEMERAL, view=MediaView(resolve, initial_quality=q))
        await aaa_log(guild, "Server icon fetch", BRAND["info"], actor=inter.user, fields={"quality": q, "url": url})

    @app_commands.command(name="server_banner", description="Download this server’s banner")
    @app_commands.describe(quality="auto|original|max")
    @app_commands.choices(quality=[
        app_commands.Choice(name="auto", value="auto"),
        app_commands.Choice(name="original", value="original"),
        app_commands.Choice(name="max", value="max"),
    ])
    async def server_banner(self, inter: discord.Interaction, quality: app_commands.Choice[str] = None):
        if not inter.guild:
            await inter.response.send_message("Use in a server", ephemeral=True)
            return
        guild = inter.guild
        asset = guild.banner or guild.discovery_splash or guild.splash
        if not asset:
            await inter.response.send_message("No banner/discovery splash/splash", ephemeral=True)
            return
        q = quality.value if quality else "auto"

        async def resolve(qv: str):
            return await _file_from_asset(asset, f"{guild.name}_banner", qv)

        file, url = await resolve(q)
        e = discord.Embed(title=f"Server Banner • {guild.name}", color=BRAND["primary"], timestamp=dt.datetime.utcnow())
        e.add_field(name="Quality", value=q, inline=True)
        e.add_field(name="CDN", value=f"`{url}`", inline=False)
        e.set_image(url=url)
        await inter.response.send_message(embed=e, file=file, ephemeral=EPHEMERAL, view=MediaView(resolve, initial_quality=q))
        await aaa_log(guild, "Server banner fetch", BRAND["info"], actor=inter.user, fields={"quality": q, "url": url})

# ========================= INVITE TRACKER (AAA) =============================
INV_CACHE: dict[int, dict[str, int]] = {}

async def _refresh_invites(guild: discord.Guild):
    try:
        invites = await guild.invites()
        INV_CACHE[guild.id] = {inv.code: (inv.uses or 0) for inv in invites}
    except Exception:
        INV_CACHE[guild.id] = {}

class Invites(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @commands.Cog.listener()
    async def on_ready(self):
        for g in bot.guilds:
            await _refresh_invites(g)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        await _refresh_invites(invite.guild)
        await aaa_log(invite.guild, "Invite created", BRAND["info"], actor=invite.inviter, fields={
            "code": invite.code,
            "max_uses": invite.max_uses,
            "temporary": invite.temporary,
        })

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        await _refresh_invites(invite.guild)
        await aaa_log(invite.guild, "Invite deleted", BRAND["warn"], fields={"code": invite.code})

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        old = INV_CACHE.get(member.guild.id, {})
        await asyncio.sleep(2)
        await _refresh_invites(member.guild)
        new = INV_CACHE.get(member.guild.id, {})
        used = None
        for code, uses in new.items():
            if uses > old.get(code, 0):
                used = code
                break
        ch = member.guild.get_channel(INVITE_TRACK_CHANNEL_ID_INT) if INVITE_TRACK_CHANNEL_ID_INT else None
        if isinstance(ch, discord.TextChannel):
            if used:
                try:
                    invite = await member.guild.fetch_invite(used)
                    inviter = invite.inviter
                    e = discord.Embed(title="👋 Willkommen!", color=BRAND["ok"])
                    e.add_field(name="Mitglied", value=f"{member.mention}", inline=True)
                    e.add_field(name="Eingeladen von", value=(inviter.mention if inviter else "Unbekannt"), inline=True)
                    e.add_field(name="Code", value=f"`{used}`", inline=True)
                    await ch.send(embed=e)
                except Exception:
                    await ch.send(f"{member.mention} ist beigetreten. Einladungscode `{used}`")
            else:
                await ch.send(f"{member.mention} ist beigetreten.")
        if used:
            try:
                invite = await member.guild.fetch_invite(used)
                inviter = invite.inviter
                await aaa_log(member.guild, "Member joined via invite", BRAND["ok"], actor=inviter, target=member,
                              fields={"code": used, "uses": invite.uses, "channel": getattr(invite.channel, "mention", None)})
            except Exception:
                await aaa_log(member.guild, "Member joined", BRAND["ok"], target=member, fields={"invite_code": used})
        else:
            await aaa_log(member.guild, "Member joined", BRAND["ok"], target=member, fields={"invite_code": "undetermined"})

# ===================== TEMP VOICE + CONTROL PANEL (AAA) =====================
class VCPanel(discord.ui.View):
    def __init__(self, vc_id: int, owner_id: int):
        super().__init__(timeout=300)
        self.vc_id = vc_id
        self.owner_id = owner_id
        self.add_item(self.LimitSelect(self))
        self.add_item(self.BitrateSelect(self))
        self.add_item(self.BtnLock(self))
        self.add_item(self.BtnRename(self))
        self.add_item(self.BtnDelete(self))

    async def _resolve(self, inter: discord.Interaction) -> t.Optional[discord.VoiceChannel]:
        ch = inter.client.get_channel(self.vc_id)
        if ch is None:
            try:
                ch = await inter.client.fetch_channel(self.vc_id)
            except Exception:
                return None
        return ch if isinstance(ch, discord.VoiceChannel) else None


    class LimitSelect(discord.ui.Select):
        def __init__(self, vp: "VCPanel"):
            opts = [discord.SelectOption(label="No limit", value="0")] + \
                   [discord.SelectOption(label=str(x), value=str(x)) for x in (2, 5, 10, 25, 99)]
            super().__init__(placeholder="User limit", options=opts, min_values=1, max_values=1)
            self.vp = vp

        async def callback(self, inter: discord.Interaction):
            if inter.user.id != self.vp.owner_id and not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=bool(inter.guild))
                return
            vc = await self.vp._resolve(inter)
            if not vc:
                await inter.response.send_message("Channel missing", ephemeral=bool(inter.guild))
                return
            val = int(self.values[0])
            try:
                await vc.edit(user_limit=val if val > 0 else 0)
                await inter.response.send_message("Updated", ephemeral=bool(inter.guild))
                await aaa_log(vc.guild, "VC user limit", BRAND["info"], actor=inter.user, fields={"channel": vc.name, "limit": val})
            except Exception as e:
                await inter.response.send_message(f"Failed: {e}", ephemeral=bool(inter.guild))


    class BitrateSelect(discord.ui.Select):
        def __init__(self, vp: "VCPanel"):
            opts = [discord.SelectOption(label="64 kbps", value="64000"),
                    discord.SelectOption(label="96 kbps", value="96000"),
                    discord.SelectOption(label="128 kbps", value="128000"),
                    discord.SelectOption(label="256 kbps", value="256000")]
            super().__init__(placeholder="Bitrate", options=opts, min_values=1, max_values=1)
            self.vp = vp

        async def callback(self, inter: discord.Interaction):
            if inter.user.id != self.vp.owner_id and not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=bool(inter.guild))
                return
            vc = await self.vp._resolve(inter)
            if not vc:
                await inter.response.send_message("Channel missing", ephemeral=bool(inter.guild))
                return
            br = int(self.values[0])
            try:
                await vc.edit(bitrate=br)
                await inter.response.send_message("Updated", ephemeral=bool(inter.guild))
                await aaa_log(vc.guild, "VC bitrate", BRAND["info"], actor=inter.user, fields={"channel": vc.name, "bitrate": br})
            except Exception as e:
                await inter.response.send_message(f"Failed: {e}", ephemeral=bool(inter.guild))


    class BtnLock(discord.ui.Button):
        def __init__(self, vp: "VCPanel"):
            super().__init__(label="Lock/Unlock", style=discord.ButtonStyle.secondary)
            self.vp = vp

        async def callback(self, inter: discord.Interaction):
            if inter.user.id != self.vp.owner_id and not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=bool(inter.guild))
                return
            vc = await self.vp._resolve(inter)
            if not vc:
                await inter.response.send_message("Channel missing", ephemeral=bool(inter.guild))
                return
            everyone = vc.guild.default_role
            try:
                current = vc.overwrites_for(everyone)
                locked = current.connect is False
                await vc.set_permissions(everyone, connect=None if locked else False)
                await inter.response.send_message("Toggled", ephemeral=bool(inter.guild))
                await aaa_log(vc.guild, "VC lock toggle", BRAND["warn"], actor=inter.user, fields={"channel": vc.name, "locked": str(not locked)})
            except Exception as e:
                await inter.response.send_message(f"Failed: {e}", ephemeral=bool(inter.guild))


    class BtnRename(discord.ui.Button):
        def __init__(self, vp: "VCPanel"):
            super().__init__(label="Rename", style=discord.ButtonStyle.primary)
            self.vp = vp

        async def callback(self, inter: discord.Interaction):
            if inter.user.id != self.vp.owner_id and not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=True)
                return
            modal = RenameModal(self.vp.vc_id)
            await inter.response.send_modal(modal)

    class BtnDelete(discord.ui.Button):
        def __init__(self, vp: "VCPanel"):
            super().__init__(label="Delete", style=discord.ButtonStyle.danger)
            self.vp = vp

        async def callback(self, inter: discord.Interaction):
            if inter.user.id != self.vp.owner_id and not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=bool(inter.guild))
                return
            vc = await self.vp._resolve(inter)
            if not vc:
                await inter.response.send_message("Channel missing", ephemeral=bool(inter.guild))
                return
            try:
                await vc.delete(reason=f"Temp VC delete by {inter.user}")
                DB["tempvc_owner"].pop(str(self.vc_id), None)
                save_db(DB)
                await inter.response.send_message("Deleted", ephemeral=bool(inter.guild))
                await aaa_log(vc.guild, "Temp VC deleted", BRAND["err"], actor=inter.user, fields={"channel_id": self.vc_id})
            except Exception as e:
                await inter.response.send_message(f"Failed: {e}", ephemeral=bool(inter.guild))


class RenameModal(discord.ui.Modal, title="Rename Voice Channel"):
    new_name = discord.ui.TextInput(label="Name", max_length=96)
    def __init__(self, vc_id: int):
        super().__init__()
        self.vc_id = vc_id
    async def on_submit(self, inter: discord.Interaction):
        ch = inter.client.get_channel(self.vc_id)
        if ch is None:
            try:
                ch = await inter.client.fetch_channel(self.vc_id)
            except Exception:
                await inter.response.send_message("Channel missing", ephemeral=bool(inter.guild))
                return
        if not isinstance(ch, discord.VoiceChannel):
            await inter.response.send_message("Channel missing", ephemeral=bool(inter.guild))
            return
        try:
            await ch.edit(name=str(self.new_name))
            await inter.response.send_message("Renamed", ephemeral=bool(inter.guild))
            await aaa_log(ch.guild, "VC rename", BRAND["info"], actor=inter.user, fields={"channel": ch.name})
        except Exception as e:
            await inter.response.send_message(f"Failed: {e}", ephemeral=bool(inter.guild))


class TempVC(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if TEMP_VC_HUB_ID_INT is None or TEMP_VC_CATEGORY_ID_INT is None:
            return
        guild = member.guild
        if after.channel and after.channel.id == TEMP_VC_HUB_ID_INT:
            category = guild.get_channel(TEMP_VC_CATEGORY_ID_INT)
            if not isinstance(category, discord.CategoryChannel):
                return
            name = f"vc-{member.name}"
            vc = await guild.create_voice_channel(name, category=category)
            DB["tempvc_owner"][str(vc.id)] = member.id
            save_db(DB)
            try:
                await member.move_to(vc)
            except Exception:
                pass
            await aaa_log(guild, "Temp VC created", BRAND["ok"], actor=member, fields={"channel": vc.name, "id": vc.id})
            try:
                await member.send(
                    embed=discord.Embed(title="Voice Control", description="Channel controller", color=BRAND["primary"]),
                    view=VCPanel(vc.id, member.id)
                )
            except Exception:
                pass
        # cleanup
        for ch in guild.voice_channels:
            if ch.category_id == TEMP_VC_CATEGORY_ID_INT and ch.id != TEMP_VC_HUB_ID_INT:
                if len(ch.members) == 0 and str(ch.id) in DB["tempvc_owner"]:
                    try:
                        await ch.delete(reason="Temp VC cleanup")
                        DB["tempvc_owner"].pop(str(ch.id), None)
                        save_db(DB)
                        await aaa_log(guild, "Temp VC auto-deleted", BRAND["muted"], fields={"channel_id": ch.id})
                    except Exception:
                        pass

    @app_commands.command(name="vc_panel", description="Open control panel for your temp voice")
    async def vc_panel(self, inter: discord.Interaction):
        if not inter.guild:
            await inter.response.send_message("Use in a server", ephemeral=True)
            return
        vc = getattr(inter.user.voice, "channel", None)
        if not isinstance(vc, discord.VoiceChannel):
            await inter.response.send_message("Join your temp VC first", ephemeral=True)
            return
        owner_id = DB["tempvc_owner"].get(str(vc.id))
        if owner_id is None:
            await inter.response.send_message("Not a temp VC", ephemeral=True)
            return
        await inter.response.send_message(embed=discord.Embed(title="Voice Control", color=BRAND["primary"]),
                                          view=VCPanel(vc.id, owner_id), ephemeral=True)

# =========================== GIVEAWAYS (AAA) ================================
class GWJoinView(discord.ui.View):
    def __init__(self, gw_id: str, admin: bool):
        super().__init__(timeout=None)
        self.gw_id = gw_id
        self.add_item(self.BtnJoin(self))
        if admin:
            self.add_item(self.BtnEnd(self))
            self.add_item(self.BtnReroll(self))
            self.add_item(self.BtnCancel(self))

    class BtnJoin(discord.ui.Button):
        def __init__(self, v: "GWJoinView"):
            super().__init__(label="Join / Leave", style=discord.ButtonStyle.success, custom_id=f"gw:join:{v.gw_id}")
            self.v = v
        async def callback(self, inter: discord.Interaction):
            gid = self.v.gw_id
            gw = DB["gw_active"].get(gid)
            if not gw:
                await inter.response.send_message("Inactive", ephemeral=True)
                return
            if inter.channel_id != int(gw["channel_id"]):
                await inter.response.send_message("Interact in the giveaway channel", ephemeral=True)
                return
            p = set(gw.setdefault("participants", []))
            uid = inter.user.id
            if uid in p:
                p.remove(uid)
            else:
                p.add(uid)
            gw["participants"] = list(p)
            save_db(DB)
            await inter.response.send_message("Updated", ephemeral=True)
            await update_gw_message(inter.client, gw)

    class BtnEnd(discord.ui.Button):
        def __init__(self, v: "GWJoinView"):
            super().__init__(label="End now", style=discord.ButtonStyle.primary, custom_id=f"gw:end:{v.gw_id}")
            self.v = v
        async def callback(self, inter: discord.Interaction):
            if not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=True)
                return
            gid = self.v.gw_id
            gw = DB["gw_active"].get(gid)
            if not gw:
                await inter.response.send_message("Inactive", ephemeral=True)
                return
            gw["ends_at"] = int(dt.datetime.utcnow().timestamp())
            save_db(DB)
            await inter.response.send_message("Ending", ephemeral=True)
            await conclude_giveaway(inter.client, gw)

    class BtnReroll(discord.ui.Button):
        def __init__(self, v: "GWJoinView"):
            super().__init__(label="Reroll", style=discord.ButtonStyle.secondary, custom_id=f"gw:reroll:{v.gw_id}")
            self.v = v
        async def callback(self, inter: discord.Interaction):
            if not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=True)
                return
            gid = self.v.gw_id
            gw = DB["gw_active"].get(gid)
            if not gw or not gw.get("winners"):
                await inter.response.send_message("No winners yet", ephemeral=True)
                return
            winners = pick_winners(gw)
            gw["winners"] = winners
            save_db(DB)
            await inter.response.send_message("Rerolled", ephemeral=True)
            await update_gw_message(inter.client, gw)
            if inter.guild:
                await aaa_log(inter.guild, "Giveaway reroll", BRAND["warn"], actor=inter.user, fields={"gw_id": gid, "winners": ", ".join(map(str, winners))})

    class BtnCancel(discord.ui.Button):
        def __init__(self, v: "GWJoinView"):
            super().__init__(label="Cancel", style=discord.ButtonStyle.danger, custom_id=f"gw:cancel:{v.gw_id}")
            self.v = v
        async def callback(self, inter: discord.Interaction):
            if not is_admin(inter.user):
                await inter.response.send_message("Not permitted", ephemeral=True)
                return
            gid = self.v.gw_id
            gw = DB["gw_active"].pop(gid, None)
            save_db(DB)
            await inter.response.send_message("Cancelled", ephemeral=True)
            if gw:
                await update_gw_message(inter.client, gw, cancelled=True)
                if inter.guild:
                    await aaa_log(inter.guild, "Giveaway cancelled", BRAND["err"], actor=inter.user, fields={"gw_id": gid})

def pick_winners(gw: dict) -> list[int]:
    k = max(1, int(gw.get("winners_count", 1)))
    ps = list(set(gw.get("participants", [])))
    if not ps:
        return []
    random.shuffle(ps)
    return ps[:k]

async def update_gw_message(client: commands.Bot, gw: dict, cancelled: bool = False):
    guild = client.get_guild(int(gw["guild_id"]))
    ch = guild.get_channel(int(gw["channel_id"])) if guild else None
    if not isinstance(ch, discord.TextChannel):
        return
    try:
        msg = await ch.fetch_message(int(gw["message_id"]))
    except Exception:
        return
    ends_at = int(gw["ends_at"])
    remaining = ends_at - int(dt.datetime.utcnow().timestamp())
    status = "Cancelled" if cancelled else ("Ended" if remaining <= 0 else f"Ends <t:{ends_at}:R>")
    entries = len(set(gw.get("participants", [])))
    prize = gw.get("prize", "")
    winners_list = gw.get("winners", [])
    e = discord.Embed(title="🎁 Giveaway", color=BRAND["primary"], timestamp=dt.datetime.utcnow())
    e.add_field(name="Prize", value=prize, inline=False)
    e.add_field(name="Status", value=status, inline=True)
    e.add_field(name="Entries", value=str(entries), inline=True)
    e.add_field(name="Winners", value=("—" if not winners_list else " ".join(f"<@{w}>" for w in winners_list)), inline=False)
    await msg.edit(embed=e, view=GWJoinView(gw["id"], admin=True))

async def conclude_giveaway(client: commands.Bot, gw: dict):
    guild = client.get_guild(int(gw["guild_id"]))
    if not guild:
        return
    winners = pick_winners(gw)
    gw["winners"] = winners
    save_db(DB)
    await update_gw_message(client, gw)
    await aaa_log(guild, "Giveaway ended", BRAND["ok"], fields={"prize": gw.get("prize"), "winners": ", ".join(map(str, winners))})

class Giveaways(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @admin_check()
    @app_commands.command(name="giveaway", description="Start a giveaway (Admin only)")
    @app_commands.describe(minutes="Duration in minutes", prize="Prize", winners="Number of winners")
    async def giveaway(self, inter: discord.Interaction, minutes: int, prize: str, winners: int = 1):
        ch = inter.channel
        if GIVEAWAY_CHANNEL_ID_INT:
            c = inter.guild.get_channel(GIVEAWAY_CHANNEL_ID_INT)
            if isinstance(c, discord.TextChannel):
                ch = c
        ends_at = int((dt.datetime.utcnow() + dt.timedelta(minutes=max(1, minutes))).timestamp())
        gid = uuid.uuid4().hex[:10]
        e = discord.Embed(title="🎁 Giveaway", color=BRAND["primary"], timestamp=dt.datetime.utcnow())
        e.add_field(name="Prize", value=prize, inline=False)
        e.add_field(name="Status", value=f"Ends <t:{ends_at}:R>", inline=True)
        e.add_field(name="Entries", value="0", inline=True)
        msg = await ch.send(embed=e, view=GWJoinView(gid, admin=True))
        DB["gw_active"][gid] = {
            "id": gid,
            "guild_id": str(inter.guild.id),
            "channel_id": str(ch.id),
            "message_id": str(msg.id),
            "prize": prize,
            "ends_at": ends_at,
            "participants": [],
            "winners_count": max(1, winners),
            "winners": []
        }
        save_db(DB)
        await inter.response.send_message(f"Created in {ch.mention}", ephemeral=True)
        await aaa_log(inter.guild, "Giveaway created", BRAND["info"], actor=inter.user, fields={"id": gid, "prize": prize, "ends_at": str(ends_at)})

        async def sleeper():
            await asyncio.sleep(max(60, minutes * 60))
            gw = DB["gw_active"].get(gid)
            if gw:
                await conclude_giveaway(self.bot, gw)
        self.bot.loop.create_task(sleeper())

# ============================== TICKETS (AAA) ===============================
class TicketOpenPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(self.BtnOpen())

    class BtnOpen(discord.ui.Button):
        def __init__(self):
            super().__init__(label="🎟️ Ticket öffnen", style=discord.ButtonStyle.primary, custom_id="ticket:open")
        async def callback(self, inter: discord.Interaction):
            await inter.response.send_modal(TicketSubjectModal())

class TicketSubjectModal(discord.ui.Modal, title="Ticket öffnen"):
    subject = discord.ui.TextInput(label="Betreff", placeholder="Kurzbeschreibung", max_length=128)
    async def on_submit(self, inter: discord.Interaction):
        await create_ticket(inter, str(self.subject))

async def create_ticket(inter: discord.Interaction, subject: str):
    guild = inter.guild
    if not guild:
        await inter.response.send_message("Guild missing", ephemeral=True)
        return
    # category + name yyyyMMdd-username
    cat = guild.get_channel(TICKET_CATEGORY_ID_INT) if TICKET_CATEGORY_ID_INT else None
    today = dt.datetime.utcnow().strftime("%Y/%m/%d")
    safe_date = today.replace("/", "-")
    name = f"{safe_date}-{inter.user.name}"[:90]
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        inter.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    ch = await guild.create_text_channel(
        name=name,
        category=cat if isinstance(cat, discord.CategoryChannel) else None,
        overwrites=overwrites
    )
    DB["tickets"][str(ch.id)] = {"opener": inter.user.id, "created": dt.datetime.utcnow().isoformat(), "subject": subject}
    save_db(DB)
    e = discord.Embed(title="Ticket", color=BRAND["primary"])
    e.add_field(name="Betreff", value=subject or "—", inline=False)
    e.add_field(name="Erstellt von", value=f"{inter.user.mention}", inline=True)
    e.add_field(name="Datum", value=today, inline=True)
    await ch.send(embed=e, view=TicketManagePanel(ch.id, inter.user.id))
    try:
        await inter.response.send_message(f"Erstellt: {ch.mention}", ephemeral=True)
    except Exception:
        pass
    await aaa_log(guild, "Ticket opened", BRAND["ok"], actor=inter.user, fields={"channel": ch.name, "subject": subject})

class TicketManagePanel(discord.ui.View):
    def __init__(self, channel_id: int, opener_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.opener_id = opener_id
        self.add_item(self.BtnTranscript(self))
        self.add_item(self.BtnClose(self))

    async def _resolve(self, inter: discord.Interaction) -> t.Optional[discord.TextChannel]:
        ch = inter.guild.get_channel(self.channel_id) if inter.guild else None
        return ch if isinstance(ch, discord.TextChannel) else None

    class BtnTranscript(discord.ui.Button):
        def __init__(self, v: "TicketManagePanel"):
            super().__init__(label="Transcript", style=discord.ButtonStyle.secondary, custom_id="ticket:transcript")
            self.v = v
        async def callback(self, inter: discord.Interaction):
            ch = await self.v._resolve(inter)
            if not ch:
                await inter.response.send_message("Channel missing", ephemeral=True)
                return
            buf = io.StringIO()
            async for m in ch.history(limit=1000, oldest_first=True):
                ts = int(m.created_at.timestamp())
                line = f"[{dt.datetime.utcfromtimestamp(ts).isoformat()}] {m.author} ({m.author.id}): {m.content}\n"
                buf.write(line)
            byts = io.BytesIO(buf.getvalue().encode("utf-8"))
            await inter.response.send_message(file=discord.File(byts, filename=f"transcript-{ch.id}.txt"), ephemeral=True)
            await aaa_log(inter.guild, "Ticket transcript", BRAND["info"], actor=inter.user, fields={"channel": ch.name})

    class BtnClose(discord.ui.Button):
        def __init__(self, v: "TicketManagePanel"):
            super().__init__(label="Close", style=discord.ButtonStyle.danger, custom_id="ticket:close")
            self.v = v
        async def callback(self, inter: discord.Interaction):
            ch = await self.v._resolve(inter)
            if not ch:
                await inter.response.send_message("Channel missing", ephemeral=True)
                return
            if not is_admin(inter.user) and inter.user.id != self.v.opener_id:
                await inter.response.send_message("Not permitted", ephemeral=True)
                return
            await aaa_log(inter.guild, "Ticket closed", BRAND["warn"], actor=inter.user, fields={"channel": ch.name})
            try:
                await ch.delete(reason=f"Ticket closed by {inter.user}")
                DB["tickets"].pop(str(ch.id), None)
                save_db(DB)
            except Exception as e:
                await inter.response.send_message(f"Failed: {e}", ephemeral=True)

class Tickets(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @app_commands.command(name="ticket_open", description="Open a private ticket")
    @app_commands.describe(subject="Short description")
    async def ticket_open(self, inter: discord.Interaction, subject: str):
        await create_ticket(inter, subject)

    @app_commands.command(name="ticket_close", description="Close this ticket (Admin only)")
    async def ticket_close(self, inter: discord.Interaction):
        ch = inter.channel
        if not isinstance(ch, discord.TextChannel):
            await inter.response.send_message("Run inside a ticket", ephemeral=True)
            return
        meta = DB["tickets"].get(str(ch.id))
        owner_id = meta["opener"] if meta else None
        if not is_admin(inter.user) and inter.user.id != owner_id:
            await inter.response.send_message("Not permitted", ephemeral=True)
            return
        await aaa_log(inter.guild, "Ticket closed", BRAND["warn"], actor=inter.user, fields={"channel": ch.name})
        try:
            await ch.delete(reason=f"Ticket closed by {inter.user}")
            DB["tickets"].pop(str(ch.id), None)
            save_db(DB)
        except Exception as e:
            await inter.response.send_message(f"Failed: {e}", ephemeral=True)

# ================ ADMIN CUSTOM EMBED /embed_send ============================
def _parse_color(s: str) -> int:
    s = (s or "").strip().lstrip("#")
    try:
        return int(s, 16)
    except Exception:
        return BRAND["primary"]

class AdminEmbed(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @admin_check()
    @app_commands.command(name="embed_send", description="Send a custom msg to any channel (Admin only)")
    @app_commands.describe(
        channel="Target channel",
        title="Embed title",
        description="Embed description (use blank line to split into spaced messages)",
        color_hex="Hex color like #5865F2",
        image_url="Optional image URL",
        thumbnail_url="Optional thumbnail URL",
        footer="Footer text",
        spaced_interval_sec="Delay in seconds between split messages (0 = disabled)",
        countdown_minutes="Add a hr:Min countdown on the FIRST message (0 = disabled)"
    )
    async def embed_send(
        self,
        inter: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str = "",
        color_hex: str = "#5865F2",
        image_url: str = "",
        thumbnail_url: str = "",
        footer: str = "",
        spaced_interval_sec: int = 0,
        countdown_minutes: int = 0,
    ):
        base_color = _parse_color(color_hex)
        parts = [p.strip() for p in (description or "").split("\n\n") if p.strip()] or [""]
        sent_messages: list[discord.Message] = []

        async def build_embed(desc_text: str) -> discord.Embed:
            e = discord.Embed(title=title, description=(desc_text or None), color=base_color)
            if image_url: e.set_image(url=image_url)
            if thumbnail_url: e.set_thumbnail(url=thumbnail_url)
            if footer: e.set_footer(text=footer)
            return e

        # send first message
        e0 = await build_embed(parts[0])
        msg0 = await channel.send(embed=e0)
        sent_messages.append(msg0)

        # spaced follow-ups
        if spaced_interval_sec > 0 and len(parts) > 1:
            for part in parts[1:]:
                await asyncio.sleep(max(1, int(spaced_interval_sec)))
                ei = await build_embed(part)
                mi = await channel.send(embed=ei)
                sent_messages.append(mi)

        # optional hr:Min countdown on FIRST message
        if countdown_minutes > 0:
            async def run_countdown(message: discord.Message, title_text: str, end_ts: int):
                try:
                    while True:
                        now = int(dt.datetime.utcnow().timestamp())
                        remaining = max(0, end_ts - now)
                        hrs = remaining // 3600
                        mins = (remaining % 3600) // 60
                        e = discord.Embed(
                            title=title_text,
                            description=parts[0] or None,
                            color=base_color
                        )
                        if image_url: e.set_image(url=image_url)
                        if thumbnail_url: e.set_thumbnail(url=thumbnail_url)
                        if footer: e.set_footer(text=footer)
                        e.add_field(name="Countdown", value=f"{hrs:02d}:{mins:02d}", inline=True)
                        try:
                            await message.edit(embed=e)
                        except Exception:
                            break
                        if remaining == 0:
                            break
                        await asyncio.sleep(60)
                except Exception:
                    pass

            end_ts = int((dt.datetime.utcnow() + dt.timedelta(minutes=max(1, int(countdown_minutes)))).timestamp())
            inter.client.loop.create_task(run_countdown(msg0, title, end_ts))

        await inter.response.send_message("Sent", ephemeral=True)
        await aaa_log(
            inter.guild,
            "Admin embed sent",
            BRAND["info"],
            actor=inter.user,
            fields={
                "channel": channel.mention,
                "title": title,
                "spaced_interval_sec": spaced_interval_sec,
                "countdown_minutes": countdown_minutes
            }
        )

    @admin_check()
    @app_commands.command(name="purge", description="Delete recent messages (Admin only)")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def purge(self, inter: discord.Interaction, amount: int):
        amount = max(1, min(100, int(amount)))
        ch = inter.channel
        if not isinstance(ch, discord.TextChannel):
            await inter.response.send_message("Run in a text channel", ephemeral=True)
            return
        try:
            deleted = await ch.purge(limit=amount, bulk=True, check=lambda m: not m.pinned)
        except Exception as ex:
            await inter.response.send_message(f"Failed: {ex}", ephemeral=True)
            return
        await inter.response.send_message(f"Deleted {len(deleted)} messages", ephemeral=True)
        await asyncio.sleep(3)
        try:
            await inter.delete_original_response()
        except Exception:
            pass
        if inter.guild:
            await aaa_log(
                inter.guild,
                "Purge",
                BRAND["warn"],
                actor=inter.user,
                fields={"channel": ch.mention, "count": len(deleted)}
            )


# ============================ SELF ROLES PANEL ==============================
SELFROLE_DRAFT: dict[tuple[int,int], dict] = {}

class SelfRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(self.OriginSelect())
        self.add_item(self.PlatformSelect())
        self.add_item(self.GenderSelect())
        self.add_item(self.AgeSelect())
        self.add_item(self.SubmitButton())

    @staticmethod
    def _draft_key(inter: discord.Interaction) -> tuple[int,int]:
        return (inter.guild.id, inter.user.id)

    class OriginSelect(discord.ui.Select):
        def __init__(self):
            opts = [discord.SelectOption(label=label, value=str(role_id)) for label, role_id in ORIGIN_OPTIONS.items()]
            super().__init__(placeholder="🌍  Choose your Origin", options=opts, min_values=0, max_values=1, custom_id="sr:origin")

        async def callback(self, inter: discord.Interaction):
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)] = SELFROLE_DRAFT.get(SelfRolesView._draft_key(inter), {})
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)]["origin"] = [int(v) for v in self.values]
            await inter.response.send_message("Origin gespeichert. Klicke auf Submit, um anzuwenden.", ephemeral=True)
            await asyncio.sleep(3)
            try:
                await inter.delete_original_response()
            except Exception:
                pass

    class PlatformSelect(discord.ui.Select):
        def __init__(self):
            opts = [discord.SelectOption(label=label, value=str(role_id)) for label, role_id in PLATFORM_OPTIONS.items()]
            super().__init__(placeholder="🕹️  Choose your Platform(s)", options=opts, min_values=0, max_values=len(opts), custom_id="sr:platform")

        async def callback(self, inter: discord.Interaction):
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)] = SELFROLE_DRAFT.get(SelfRolesView._draft_key(inter), {})
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)]["platform"] = [int(v) for v in self.values]
            await inter.response.send_message("Platform gespeichert. Klicke auf Submit, um anzuwenden.", ephemeral=True)
            await asyncio.sleep(3)
            try:
                await inter.delete_original_response()
            except Exception:
                pass

    class GenderSelect(discord.ui.Select):
        def __init__(self):
            opts = [discord.SelectOption(label=label, value=str(role_id)) for label, role_id in GENDER_OPTIONS.items()]
            super().__init__(placeholder="⚧️  Choose your Gender", options=opts, min_values=0, max_values=1, custom_id="sr:gender")

        async def callback(self, inter: discord.Interaction):
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)] = SELFROLE_DRAFT.get(SelfRolesView._draft_key(inter), {})
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)]["gender"] = [int(v) for v in self.values]
            await inter.response.send_message("Gender gespeichert. Klicke auf Submit, um anzuwenden.", ephemeral=True)
            await asyncio.sleep(3)
            try:
                await inter.delete_original_response()
            except Exception:
                pass

    class AgeSelect(discord.ui.Select):
        def __init__(self):
            opts = [discord.SelectOption(label=label, value=str(role_id)) for label, role_id in ABOUT_OPTIONS.items()]
            super().__init__(placeholder="🔞  Choose your Age", options=opts, min_values=0, max_values=1, custom_id="sr:age")

        async def callback(self, inter: discord.Interaction):
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)] = SELFROLE_DRAFT.get(SelfRolesView._draft_key(inter), {})
            SELFROLE_DRAFT[SelfRolesView._draft_key(inter)]["age"] = [int(v) for v in self.values]
            await inter.response.send_message("About Me gespeichert. Klicke auf Submit, um anzuwenden.", ephemeral=True)
            await asyncio.sleep(3)
            try:
                await inter.delete_original_response()
            except Exception:
                pass


    class SubmitButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Submit", style=discord.ButtonStyle.primary, custom_id="sr:submit")
        async def callback(self, inter: discord.Interaction):
            key = SelfRolesView._draft_key(inter)
            draft = SELFROLE_DRAFT.get(key, {})
            member: discord.Member = inter.user  # type: ignore
            changes = []
            # Origin (exclusive)
            if "origin" in draft:
                current = [rid for rid in ORIGIN_OPTIONS.values() if member.get_role(rid)]
                for rid in current:
                    if rid not in draft["origin"]:
                        r = inter.guild.get_role(rid)
                        if r:
                            await member.remove_roles(r, reason="Origin change"); changes.append(f"-{r.name}")
                for rid in draft["origin"]:
                    r = inter.guild.get_role(rid)
                    if r and not member.get_role(rid):
                        await member.add_roles(r, reason="Origin add"); changes.append(f"+{r.name}")
            # enforce mandatory parent
            parent = inter.guild.get_role(ORIGIN_PARENT)
            if parent:
                has_any = any(member.get_role(rid) for rid in ORIGIN_OPTIONS.values())
                if has_any and not member.get_role(ORIGIN_PARENT):
                    await member.add_roles(parent, reason="Origin parent grant"); changes.append(f"+{parent.name}")
                elif not has_any and member.get_role(ORIGIN_PARENT):
                    await member.remove_roles(parent, reason="Origin parent remove"); changes.append(f"-{parent.name}")
            # Platform (multi)
            if "platform" in draft:
                for rid in PLATFORM_OPTIONS.values():
                    if member.get_role(rid) and rid not in draft["platform"]:
                        r = inter.guild.get_role(rid)
                        if r:
                            await member.remove_roles(r, reason="Platform change"); changes.append(f"-{r.name}")
                for rid in draft["platform"]:
                    r = inter.guild.get_role(rid)
                    if r and not member.get_role(rid):
                        await member.add_roles(r, reason="Platform add"); changes.append(f"+{r.name}")
            # enforce mandatory parent
            parent = inter.guild.get_role(PLATFORM_PARENT)
            if parent:
                has_any = any(member.get_role(rid) for rid in PLATFORM_OPTIONS.values())
                if has_any and not member.get_role(PLATFORM_PARENT):
                    await member.add_roles(parent, reason="Platform parent grant"); changes.append(f"+{parent.name}")
                elif not has_any and member.get_role(PLATFORM_PARENT):
                    await member.remove_roles(parent, reason="Platform parent remove"); changes.append(f"-{parent.name}")
            # Gender (exclusive)
            # Gender (exclusive)
            if "gender" in draft:
                current = [rid for rid in GENDER_OPTIONS.values() if member.get_role(rid)]
                for rid in current:
                    if rid not in draft["gender"]:
                        r = inter.guild.get_role(rid)
                        if r:
                            await member.remove_roles(r, reason="Gender change"); changes.append(f"-{r.name}")
                for rid in draft["gender"]:
                    r = inter.guild.get_role(rid)
                    if r and not member.get_role(rid):
                        await member.add_roles(r, reason="Gender add"); changes.append(f"+{r.name}")
            # enforce mandatory parent
            parent = inter.guild.get_role(GENDER_PARENT)
            if parent:
                has_any = any(member.get_role(rid) for rid in GENDER_OPTIONS.values())
                if has_any and not member.get_role(GENDER_PARENT):
                    await member.add_roles(parent, reason="Gender parent grant"); changes.append(f"+{parent.name}")
                elif not has_any and member.get_role(GENDER_PARENT):
                    await member.remove_roles(parent, reason="Gender parent remove"); changes.append(f"-{parent.name}")

            # About (exclusive)
            if "age" in draft:
                current = [rid for rid in ABOUT_OPTIONS.values() if member.get_role(rid)]
                for rid in current:
                    if rid not in draft["age"]:
                        r = inter.guild.get_role(rid)
                        if r:
                            await member.remove_roles(r, reason="About change"); changes.append(f"-{r.name}")
                for rid in draft["age"]:
                    r = inter.guild.get_role(rid)
                    if r and not member.get_role(rid):
                        await member.add_roles(r, reason="About add"); changes.append(f"+{r.name}")
            # enforce mandatory parent
            parent = inter.guild.get_role(ABOUT_PARENT)
            if parent:
                has_any = any(member.get_role(rid) for rid in ABOUT_OPTIONS.values())
                if has_any and not member.get_role(ABOUT_PARENT):
                    await member.add_roles(parent, reason="About parent grant"); changes.append(f"+{parent.name}")
                elif not has_any and member.get_role(ABOUT_PARENT):
                    await member.remove_roles(parent, reason="About parent remove"); changes.append(f"-{parent.name}")

            SELFROLE_DRAFT.pop(key, None)
            await inter.response.send_message("Roles updated", ephemeral=True)

class SelfRoles(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

# ======================= LEVELS + COUNTING + GUARD ==========================
TOKEN_RE = re.compile(r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}")
INVITE_RE = re.compile(r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)", re.I)
LINK_RE = re.compile(r"https?://", re.I)

def level_for_xp(total_xp: int) -> int:
    # hard progression: cumulative threshold grows fast (target: lvl50 is very hard)
    # per-level requirement ~ 300 + 40*n + 5*n^2
    lvl = 0
    needed = 0
    while True:
        n = lvl + 1
        need = 300 + 40*n + 5*(n*n)   # per next level
        if total_xp < needed + need:
            return lvl
        needed += need
        lvl += 1

LEVEL_ROLES = {
    10: ROLE_L10,
    15: ROLE_L15,
    20: ROLE_L20,
    25: ROLE_L25,
    50: ROLE_L50,
}

class ActivityGuard(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not msg.guild or msg.author.bot:
            return

        # Counting game — dedicated channel (skip further processing)
        if COUNTING_CHANNEL_ID_INT and msg.channel.id == COUNTING_CHANNEL_ID_INT:
            await self._counting(msg)
            return

        # Dangerous content guard (admins bypass)
        content = msg.content or ""
        if not is_admin(msg.author):
            if INVITE_RE.search(content) or LINK_RE.search(content) or TOKEN_RE.search(content) or "secret" in content.lower():
                try:
                    await msg.delete()
                except Exception:
                    pass
                red = INVITE_RE.sub("[invite]", content)
                red = TOKEN_RE.sub("[secret]", red)
                await aaa_log(msg.guild, "Blocked content", BRAND["err"], actor=msg.author,
                              fields={"channel": msg.channel.mention, "snippet": red[:400]})
                return

        # Levels (cooldown per user per guild)
        now = int(dt.datetime.utcnow().timestamp())
        gkey = str(msg.guild.id)
        ukey = str(msg.author.id)
        cooldowns = DB.setdefault("xp_cooldowns", {}).setdefault(gkey, {})
        next_ok = int(cooldowns.get(ukey, 0))
        if now >= next_ok:
            xp_store = DB.setdefault("xp", {}).setdefault(gkey, {})
            total = int(xp_store.get(ukey, 0))
            gain = random.randint(12, 22)  # modest
            total += gain
            xp_store[ukey] = total
            cooldowns[ukey] = now + 60
            save_db(DB)
            # Level up?
            new_lvl = level_for_xp(total)
            prev_total = total - gain
            old_lvl = level_for_xp(prev_total)
            if new_lvl > old_lvl and LEVEL_ANNOUNCE_CHANNEL_ID_INT:
                ch = msg.guild.get_channel(LEVEL_ANNOUNCE_CHANNEL_ID_INT)
                if isinstance(ch, discord.TextChannel):
                    e = discord.Embed(title="⬆️ Level Up", color=BRAND["ok"])
                    e.add_field(name="User", value=f"{msg.author.mention}", inline=True)
                    e.add_field(name="Level", value=str(new_lvl), inline=True)
                    await ch.send(embed=e)
                # Role rewards (grant when crossing threshold)
                for req, rid in LEVEL_ROLES.items():
                    role = msg.guild.get_role(rid)
                    if role and new_lvl >= req and role not in msg.author.roles:
                        try: await msg.author.add_roles(role, reason=f"Reached level {req}")
                        except Exception: pass

    async def _counting(self, msg: discord.Message):
        gkey = str(msg.guild.id)
        data = DB.setdefault("counting", {}).setdefault(gkey, {"last": 0, "last_user": 0})
        last = int(data.get("last", 0))
        last_user = int(data.get("last_user", 0))
        content = msg.content.strip()
        try:
            num = int(content)
        except Exception:
            await self._count_fail(msg, "Keine Zahl erkannt.")
            DB["counting"][gkey] = {"last": 0, "last_user": 0}
            save_db(DB)
            return
        if num != last + 1:
            await self._count_fail(msg, f"Falsch. Erwartet war {last+1}.")
            DB["counting"][gkey] = {"last": 0, "last_user": 0}
            save_db(DB)
            return
        if msg.author.id == last_user:
            await self._count_fail(msg, "Zweimal hintereinander zählt nicht.")
            DB["counting"][gkey] = {"last": 0, "last_user": 0}
            save_db(DB)
            return
        try:
            await msg.add_reaction("✅")
        except Exception:
            pass
        DB["counting"][gkey]["last"] = num
        DB["counting"][gkey]["last_user"] = msg.author.id
        save_db(DB)

    async def _count_fail(self, msg: discord.Message, reason: str):
        lines = [
            "Ups, das war nichts. Versuch’s nochmal!",
            "Das zählt nicht. Einmal tief durchatmen, dann weiter.",
            "Falsch gezählt. Zahlen sind hart, ich weiß.",
            "Nein. Zurück auf Anfang.",
            "Leider daneben. Neustart bei 1."
        ]
        try:
            await msg.channel.send(f"{msg.author.mention} {random.choice(lines)} Grund: {reason}")
        except Exception:
            pass

# ============================= LOGGING (AAA) ================================
class Logging(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        if msg.guild and not msg.author.bot:
            red = INVITE_RE.sub("[invite]", msg.content or "")
            red = TOKEN_RE.sub("[secret]", red)
            await aaa_log(msg.guild, "Message deleted", BRAND["warn"], actor=msg.author, fields={
                "channel": msg.channel.mention, "content": red[:400]
            })

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild and not before.author.bot and (before.content or "") != (after.content or ""):
            b = INVITE_RE.sub("[invite]", before.content or "")
            b = TOKEN_RE.sub("[secret]", b)
            a = INVITE_RE.sub("[invite]", after.content or "")
            a = TOKEN_RE.sub("[secret]", a)
            await aaa_log(before.guild, "Message edited", BRAND["info"], actor=before.author, fields={
                "channel": before.channel.mention, "before": b[:300], "after": a[:300]
            })

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        # find actor from audit logs
        actor, reason = None, None
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id and (dt.datetime.utcnow() - entry.created_at.replace(tzinfo=None)).total_seconds() < 30:
                    actor, reason = entry.user, entry.reason
                    break
        except Exception:
            pass
        await aaa_log(guild, "Ban", BRAND["err"], actor=actor, target=user, fields={"reason": reason})

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # detect kick
        actor, reason, kicked = None, None, False
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id and (dt.datetime.utcnow() - entry.created_at.replace(tzinfo=None)).total_seconds() < 30:
                    actor, reason, kicked = entry.user, entry.reason, True
                    break
        except Exception:
            pass
        if kicked:
            await aaa_log(member.guild, "Kick", BRAND["warn"], actor=actor, target=member, fields={"reason": reason})
        else:
            await aaa_log(member.guild, "Member left", BRAND["muted"], target=member)

# ======================= STARTUP SEEDERS / PERSISTENT =======================
async def seed_ticket_panel(guild: discord.Guild):
    ch = guild.get_channel(TICKET_PANEL_CHANNEL_ID_INT) if TICKET_PANEL_CHANNEL_ID_INT else None
    if not isinstance(ch, discord.TextChannel):
        return
    msg_id = DB.get("ticket_panel_msg_id")
    need_send = True
    if msg_id:
        try:
            _ = await ch.fetch_message(int(msg_id))
            need_send = False
        except Exception:
            need_send = True
    if need_send:
        e = discord.Embed(title="German Voice World Support", description="Klicke unten, um ein Ticket zu öffnen.", color=BRAND["primary"])
        msg = await ch.send(embed=e, view=TicketOpenPanel())
        DB["ticket_panel_msg_id"] = str(msg.id)
        save_db(DB)

async def seed_selfroles_panel(guild: discord.Guild):
    ch = guild.get_channel(SELFROLES_CHANNEL_ID_INT) if SELFROLES_CHANNEL_ID_INT else None
    if not isinstance(ch, discord.TextChannel):
        return
    msg_id = DB.get("selfroles_panel_msg_id")
    need_send = True
    if msg_id:
        try:
            _ = await ch.fetch_message(int(msg_id))
            need_send = False
        except Exception:
            need_send = True
    if need_send:
        e = discord.Embed(title="Rollen Auswahl", description="Wähle Kategorien aus und klicke auf **Submit**.", color=BRAND["primary"])
        msg = await ch.send(embed=e, view=SelfRolesView())
        DB["selfroles_panel_msg_id"] = str(msg.id)
        save_db(DB)

async def restore_giveaway_views(guild: discord.Guild):
    # re-bind persistent views for active giveaways
    for gid, gw in list(DB.get("gw_active", {}).items()):
        if int(gw.get("guild_id", 0)) == guild.id:
            bot.add_view(GWJoinView(gid, admin=True))

# ============================ BOOTSTRAP =====================================
async def setup_all():
    await bot.add_cog(Media(bot))
    await bot.add_cog(Invites(bot))
    await bot.add_cog(TempVC(bot))
    await bot.add_cog(Giveaways(bot))
    await bot.add_cog(Tickets(bot))
    await bot.add_cog(AdminEmbed(bot))
    await bot.add_cog(SelfRoles(bot))
    await bot.add_cog(ActivityGuard(bot))
    await bot.add_cog(Logging(bot))

    # Persistent component bindings (so buttons survive restarts)
    bot.add_view(TicketOpenPanel())
    bot.add_view(SelfRolesView())

import itertools

STATUS_ROTATE = itertools.cycle([
    ("online", "Moderation aktiv"),
    ("online", "Tickets offen"),
    ("online", "Logs laufen"),
    ("online", "Rollen bereit"),
    ("online", "Level aktiv"),
    ("online", "Voice-Kontrolle"),
    ("online", "Giveaways bereit"),
    ("online", "Serverschutz"),
    ("online", "Einladungen prüfen"),
    ("online", "System stabil"),
])

async def rotate_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        _, text = next(STATUS_ROTATE)
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name=text)
        )
        await asyncio.sleep(120)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    # mount cogs/views
    await setup_all()
    # seed panels & restore views
    for g in bot.guilds:
        await seed_ticket_panel(g)
        await seed_selfroles_panel(g)
        await restore_giveaway_views(g)
        bot.loop.create_task(rotate_status())
    # sync commands AFTER login (avoids application_id error)
    try:
        if GUILD_ID_INT:
            guild_obj = discord.Object(id=GUILD_ID_INT)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"🔁 Synced {len(synced)} guild commands to {GUILD_ID_INT}")
        else:
            synced = await bot.tree.sync()
            print(f"🔁 Synced {len(synced)} global commands")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)
