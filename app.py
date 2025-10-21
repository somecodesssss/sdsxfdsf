import os

CONFIG = {
    "DISCORD_TOKEN": os.environ["DISCORD_TOKEN"],            # from Render env
    "GUILD_ID": 1270144230525763697,
    "ADMIN_ROLE_ID": 1415349148944699453,
    "ROBLOX_UNIVERSE_ID": int(os.environ["ROBLOX_UNIVERSE_ID"]),  # from Render env
    "ROBLOSECURITY": os.environ["ROBLOSECURITY"],            # from Render env
    "TRACK_INTERVAL_SECONDS": 3,
    "SCAN_MAX_PAGES": 8,
    "SCAN_ITEM_LIMIT": 800,
    "COMMANDS_EPHEMERAL": True,
}

import asyncio
import random
from dataclasses import dataclass
from typing import Optional, Any, AsyncIterator, List

import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp


def _to_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, int):
            return v
        s = str(v).strip()
        return int(s) if s.isdigit() else None
    except Exception:
        return None


class Settings:
    def __init__(self, cfg: dict):
        token = str(cfg.get("DISCORD_TOKEN", "")).strip()
        admin_role_id = _to_int(cfg.get("ADMIN_ROLE_ID"))
        universe_id = _to_int(cfg.get("ROBLOX_UNIVERSE_ID"))
        if not token or token in ("REPLACE_ME",):
            raise SystemExit("CONFIG: DISCORD_TOKEN missing/invalid")
        if not admin_role_id:
            raise SystemExit("CONFIG: ADMIN_ROLE_ID missing/invalid")
        if not universe_id:
            raise SystemExit("CONFIG: ROBLOX_UNIVERSE_ID missing/invalid")

        guild_id = _to_int(cfg.get("GUILD_ID")) or 0
        cookie = str(cfg.get("ROBLOSECURITY", "")).strip() or None

        interval = _to_int(cfg.get("TRACK_INTERVAL_SECONDS")) or 5
        if interval < 3:
            interval = 3
        pages = _to_int(cfg.get("SCAN_MAX_PAGES")) or 8
        if pages < 1:
            pages = 1
        limit = _to_int(cfg.get("SCAN_ITEM_LIMIT")) or 800
        if limit < 100:
            limit = 100
        ephemeral = bool(cfg.get("COMMANDS_EPHEMERAL", True))

        self.token: str = token
        self.guild_id: int = guild_id
        self.admin_role_id: int = admin_role_id
        self.universe_id: int = universe_id
        self.cookie: Optional[str] = cookie
        self.interval: int = interval
        self.pages: int = pages
        self.limit: int = limit
        self.ephemeral: bool = ephemeral


SETTINGS = Settings(CONFIG)
intents = discord.Intents.default()


@dataclass
class UniverseDetails:
    name: str
    playing: int
    visits: int
    favorites: Optional[int]
    root_place_id: Optional[int]


class RobloxClient:
    BASE_GAMES = "https://games.roblox.com"
    UA = "rbx-track-bot/1.4 (+discord)"
    T_CONN = 8
    T_TOTAL = 20
    RETRIES = 4
    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self, session: aiohttp.ClientSession, cookie: Optional[str]):
        self.session = session
        self.cookie = cookie

    def _auth_headers(self) -> dict:
        return {"Cookie": f".ROBLOSECURITY={self.cookie};"} if self.cookie else {}

    async def _request(self, method: str, url: str, **kwargs) -> Optional[dict]:
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", self.UA)
        headers.setdefault("Accept", "application/json")
        headers.update(self._auth_headers())
        timeout = aiohttp.ClientTimeout(total=self.T_TOTAL, connect=self.T_CONN)
        backoff = 0.6
        for _ in range(self.RETRIES):
            try:
                async with self.session.request(method, url, headers=headers, timeout=timeout, **kwargs) as r:
                    if r.status == 200:
                        try:
                            return await r.json()
                        except Exception:
                            return None
                    if r.status in self.RETRY_STATUSES:
                        await asyncio.sleep(backoff + random.random() * 0.3)
                        backoff *= 1.8
                        continue
                    return None
            except Exception:
                await asyncio.sleep(backoff + random.random() * 0.3)
                backoff *= 1.8
        return None

    async def get_universe_details(self, universe_id: int) -> Optional[UniverseDetails]:
        url = f"{self.BASE_GAMES}/v1/games?universeIds={universe_id}"
        data = await self._request("GET", url)
        if not data or "data" not in data or not isinstance(data["data"], list) or not data["data"]:
            return None
        g = data["data"][0]
        name = str(g.get("name", "Game"))
        playing = int(g.get("playing", 0) or 0)
        visits = int(g.get("visits", 0) or 0)
        fav_raw = g.get("favoritedCount", g.get("favorites"))
        favorites = int(fav_raw) if isinstance(fav_raw, (int, float)) else None
        rp = g.get("rootPlaceId")
        root_place_id = int(rp) if isinstance(rp, (int, float, str)) and str(rp).isdigit() else None
        return UniverseDetails(name=name, playing=playing, visits=visits, favorites=favorites, root_place_id=root_place_id)

    async def iter_public_servers(self, place_id: int, page_limit: int, item_limit: int) -> AsyncIterator[dict]:
        cursor = None
        fetched = 0
        for _ in range(page_limit):
            params = {"sortOrder": "Desc", "limit": "100"}
            if cursor:
                params["cursor"] = cursor
            url = f"{self.BASE_GAMES}/v1/games/{place_id}/servers/Public"
            data = await self._request("GET", url, params=params)
            if not data or "data" not in data or not isinstance(data["data"], list):
                break
            for item in data["data"]:
                yield item
                fetched += 1
                if fetched >= item_limit:
                    return
            cursor = data.get("nextPageCursor")
            if not cursor:
                break

    async def count_and_sum_public_servers(self, place_id: int, page_limit: int, item_limit: int) -> tuple[int, int]:
        count = 0
        total_players = 0
        async for s in self.iter_public_servers(place_id, page_limit, item_limit):
            count += 1
            try:
                total_players += int(s.get("playing", 0) or 0)
            except Exception:
                pass
        return count, total_players


def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        m = interaction.user
        if not isinstance(m, discord.Member):
            raise app_commands.CheckFailure("ADMIN_ROLE_REQUIRED")
        if any(r.id == SETTINGS.admin_role_id for r in m.roles):
            return True
        raise app_commands.CheckFailure("ADMIN_ROLE_REQUIRED")
    return app_commands.check(predicate)


class RBXBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.rblx: Optional[RobloxClient] = None
        self.universe_id: int = SETTINGS.universe_id
        self.root_place_id: Optional[int] = None
        self.scan_pages: int = SETTINGS.pages
        self.scan_limit: int = SETTINGS.limit
        # debounced zero handling
        self.prev_servers: int = -1
        self.prev_players_sum: int = -1
        self.zero_streak: int = 0

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25, connect=8))
        self.rblx = RobloxClient(self.http_session, SETTINGS.cookie)
        if SETTINGS.guild_id and SETTINGS.guild_id > 0:
            guild_obj = discord.Object(id=SETTINGS.guild_id)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        try:
            if self.http_session and not self.http_session.closed:
                await self.http_session.close()
        finally:
            await super().close()


bot = RBXBot()


async def _presence_once():
    uid = bot.universe_id
    if not uid or not bot.rblx:
        return

    # Always refresh universe to get authoritative "playing" (includes non-public servers)
    d = await bot.rblx.get_universe_details(uid)
    if not d:
        return
    if bot.root_place_id is None and d.root_place_id:
        bot.root_place_id = d.root_place_id
    if not bot.root_place_id:
        # Fall back to universe "playing" if we don't yet know the root place
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"0 servers | {max(int(d.playing or 0), 0)} players",
            )
        )
        return

    # Fresh scan of public servers
    try:
        servers, players_sum = await bot.rblx.count_and_sum_public_servers(
            bot.root_place_id,
            page_limit=bot.scan_pages,
            item_limit=bot.scan_limit,
        )
        servers = int(servers or 0)
        players_sum = int(players_sum or 0)
    except Exception:
        # On failure, fall back to last nonzero or universe "playing"
        servers = bot.prev_servers if bot.prev_servers > 0 else 0
        players_sum = bot.prev_players_sum if bot.prev_players_sum > 0 else int(d.playing or 0)

    # If scan says zero but universe reports players, prefer universe count (players may be in private/reserved servers)
    if servers == 0 and players_sum == 0 and int(d.playing or 0) > 0:
        players_sum = int(d.playing)
        servers = max(bot.prev_servers, 1)

    # Debounce a single transient zero tick
    if servers == 0 and players_sum == 0 and (bot.prev_servers > 0 or bot.prev_players_sum > 0):
        if bot.zero_streak == 0:
            servers = max(bot.prev_servers, 0)
            players_sum = max(bot.prev_players_sum, 0)
        bot.zero_streak = 1
    else:
        bot.zero_streak = 0

    # Persist last values
    bot.prev_servers = servers
    bot.prev_players_sum = players_sum

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{servers} servers | {players_sum} players",
        )
    )


@tasks.loop(seconds=SETTINGS.interval)
async def presence_loop():
    try:
        await _presence_once()
    except Exception:
        pass


@presence_loop.before_loop
async def _presence_wait_ready():
    await bot.wait_until_ready()


async def _fetch_json(url: str) -> Optional[dict]:
    try:
        assert bot.http_session is not None
        async with bot.http_session.get(url, headers={"User-Agent": "rbx-track-bot/1.4"}) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = "Error."
    if isinstance(error, app_commands.CheckFailure):
        msg = "You lack permission."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=SETTINGS.ephemeral)
        else:
            await interaction.response.send_message(msg, ephemeral=SETTINGS.ephemeral)
    except Exception:
        pass


@bot.tree.command(description="Live players and basic stats")
async def players(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=SETTINGS.ephemeral, thinking=True)
    uid = bot.universe_id
    if not uid or not bot.rblx:
        await interaction.followup.send("Not configured.", ephemeral=SETTINGS.ephemeral)
        return
    d = await bot.rblx.get_universe_details(uid)
    if not d:
        await interaction.followup.send("No data.", ephemeral=SETTINGS.ephemeral)
        return
    e = discord.Embed(title=f"{d.name} — Live Players", color=0x57F287)
    e.add_field(name="Universe Playing Now", value=str(d.playing))
    e.add_field(name="Visits", value=str(d.visits))
    if d.favorites is not None:
        e.add_field(name="Favorites", value=str(d.favorites))
    if bot.root_place_id:
        try:
            servers, players_sum = await bot.rblx.count_and_sum_public_servers(
                bot.root_place_id, bot.scan_pages, bot.scan_limit
            )
            e.add_field(name="Public Servers", value=str(servers), inline=True)
            e.add_field(name="Players In Public Servers", value=str(players_sum), inline=True)
        except Exception:
            pass
    if d.root_place_id:
        e.set_footer(text=f"Universe {uid} • Place {d.root_place_id}")
    await interaction.followup.send(embed=e, ephemeral=SETTINGS.ephemeral)


@bot.tree.command(description="Top public servers with join links")
@app_commands.describe(limit="1–20 (default 10)")
async def servers(interaction: discord.Interaction, limit: app_commands.Range[int, 1, 20] = 10):
    await interaction.response.defer(ephemeral=SETTINGS.ephemeral, thinking=True)
    uid = bot.universe_id
    if not uid or not bot.rblx:
        await interaction.followup.send("Not configured.", ephemeral=SETTINGS.ephemeral)
        return
    d = await bot.rblx.get_universe_details(uid)
    if not d or not d.root_place_id:
        await interaction.followup.send("Root place unavailable.", ephemeral=SETTINGS.ephemeral)
        return
    items: List[dict] = []
    total_players = 0
    async for s in bot.rblx.iter_public_servers(d.root_place_id, page_limit=bot.scan_pages, item_limit=bot.scan_limit):
        items.append(s)
        try:
            total_players += int(s.get("playing", 0) or 0)
        except Exception:
            pass
    if not items:
        await interaction.followup.send("No public servers found.", ephemeral=SETTINGS.ephemeral)
        return
    items.sort(key=lambda x: x.get("playing", 0), reverse=True)
    top = items[:limit]
    lines = []
    for i, s in enumerate(top, 1):
        playing = s.get("playing", 0)
        maxp = s.get("maxPlayers", "?")
        ping = s.get("ping", "–")
        sid = s.get("id", "")
        if sid and d.root_place_id:
            web = f"https://www.roblox.com/games/start?placeId={d.root_place_id}&gameInstanceId={sid}"
            app = f"roblox://placeId={d.root_place_id}&gameInstanceId={sid}"
            line = f"**#{i}** — {playing}/{maxp} | ping {ping}\n↳ [join:web]({web}) • [join:app]({app})"
        else:
            line = f"**#{i}** — {playing}/{maxp} | ping {ping}"
        lines.append(line)
    e = discord.Embed(title=f"Active Public Servers — {d.name}", description="\n".join(lines), color=0x2b2d31)
    e.set_footer(text=f"Scanned {len(items)} servers • {total_players} players across scanned servers")
    await interaction.followup.send(embed=e, ephemeral=SETTINGS.ephemeral)


@bot.tree.command(description="Count active public servers (deep scan)")
async def servercount(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=SETTINGS.ephemeral, thinking=True)
    uid = bot.universe_id
    if not uid or not bot.rblx:
        await interaction.followup.send("Not configured.", ephemeral=SETTINGS.ephemeral)
        return
    d = await bot.rblx.get_universe_details(uid)
    if not d or not d.root_place_id:
        await interaction.followup.send("Root place unavailable.", ephemeral=SETTINGS.ephemeral)
        return
    servers, players_sum = await bot.rblx.count_and_sum_public_servers(
        d.root_place_id, page_limit=bot.scan_pages, item_limit=bot.scan_limit
    )
    await interaction.followup.send(
        f"Active public servers: **{servers}** • players across public servers: **{players_sum}**",
        ephemeral=SETTINGS.ephemeral,
    )


@bot.tree.command(description="Lowest ping public servers")
@app_commands.describe(limit="1–10 (default 5)")
async def lowestping(interaction: discord.Interaction, limit: app_commands.Range[int, 1, 10] = 5):
    await interaction.response.defer(ephemeral=SETTINGS.ephemeral, thinking=True)
    uid = bot.universe_id
    if not uid or not bot.rblx:
        await interaction.followup.send("Not configured.", ephemeral=SETTINGS.ephemeral)
        return
    d = await bot.rblx.get_universe_details(uid)
    if not d or not d.root_place_id:
        await interaction.followup.send("Root place unavailable.", ephemeral=SETTINGS.ephemeral)
        return
    items: List[dict] = []
    async for s in bot.rblx.iter_public_servers(d.root_place_id, page_limit=bot.scan_pages, item_limit=bot.scan_limit):
        if isinstance(s.get("ping"), (int, float)):
            items.append(s)
    if not items:
        await interaction.followup.send("No servers with ping data.", ephemeral=SETTINGS.ephemeral)
        return
    items.sort(key=lambda x: x.get("ping", 1e9))
    top = items[:limit]
    lines = []
    for i, s in enumerate(top, 1):
        playing = s.get("playing", 0)
        maxp = s.get("maxPlayers", "?")
        ping = s.get("ping", "–")
        sid = s.get("id", "")
        if sid and d.root_place_id:
            web = f"https://www.roblox.com/games/start?placeId={d.root_place_id}&gameInstanceId={sid}"
            app = f"roblox://placeId={d.root_place_id}&gameInstanceId={sid}"
            line = f"**#{i}** — {playing}/{maxp} | ping {ping}\n↳ [join:web]({web}) • [join:app]({app})"
        else:
            line = f"**#{i}** — {playing}/{maxp} | ping {ping}"
        lines.append(line)
    e = discord.Embed(title=f"Lowest Ping Servers — {d.name}", description="\n".join(lines), color=0x5865F2)
    await interaction.followup.send(embed=e, ephemeral=SETTINGS.ephemeral)


@bot.tree.command(description="Create a join link for a specific instance ID")
@app_commands.describe(instance_id="Roblox server instance ID")
async def join(interaction: discord.Interaction, instance_id: str):
    await interaction.response.defer(ephemeral=SETTINGS.ephemeral, thinking=True)
    if not bot.root_place_id:
        await interaction.followup.send("Root place unavailable.", ephemeral=SETTINGS.ephemeral)
        return
    web = f"https://www.roblox.com/games/start?placeId={bot.root_place_id}&gameInstanceId={instance_id}"
    app = f"roblox://placeId={bot.root_place_id}&gameInstanceId={instance_id}"
    await interaction.followup.send(f"[join:web]({web}) • [join:app]({app})", ephemeral=SETTINGS.ephemeral)


_MEME_API_BASE = "https://meme-api.com/gimme"
_SAFE_FALLBACK_GIFS = [
    "https://media.tenor.com/9I7bVJfL2OIAAAAd/thumbs-up.gif",
    "https://media.tenor.com/Mm4Q3KQ2i-4AAAAd/hype.gif",
    "https://media.tenor.com/HL6m1q0wSSEAAAAd/party-parrot.gif",
]


@bot.tree.command(description="Random meme (optional subreddit)")
@app_commands.describe(subreddit="Pick a subreddit (default: random)")
async def meme(interaction: discord.Interaction, subreddit: Optional[str] = None):
    await interaction.response.defer(ephemeral=SETTINGS.ephemeral, thinking=True)
    url = _MEME_API_BASE + (f"/{subreddit}" if subreddit else "")
    data = await _fetch_json(url)
    if not data:
        await interaction.followup.send("Couldn't fetch a meme right now.", ephemeral=SETTINGS.ephemeral)
        return
    if data.get("nsfw"):
        await interaction.followup.send("NSFW meme skipped.", ephemeral=SETTINGS.ephemeral)
        return
    e = discord.Embed(title=data.get("title", "Meme"), url=data.get("postLink"), color=0x2b2d31)
    if data.get("subreddit"):
        e.set_footer(text=f"r/{data.get('subreddit')}")
    if data.get("url"):
        e.set_image(url=data["url"])
    await interaction.followup.send(embed=e, ephemeral=SETTINGS.ephemeral)


@bot.tree.command(description="Search a GIF without API keys (keyword→subreddits)")
@app_commands.describe(query="Keyword, e.g., 'roblox', 'cat', 'dance'")
async def gif(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=SETTINGS.ephemeral, thinking=True)
    keymap = {
        "roblox": ["robloxmemes", "roblox"],
        "cat": ["CatGifs", "catsstandingup", "KittenGifs"],
        "dog": ["doggifs", "rarepuppers"],
        "dance": ["DanceGifs", "HighQualityGifs"],
        "fail": ["instant_regret", "holdmybeer"],
        "german": ["Germany", "ich_iel"],
        "meme": ["memes", "dankmemes", "wholesomememes"],
        "reaction": ["reactiongifs", "HighQualityGifs"],
    }
    defaults = ["gif", "gifs", "reactiongifs", "HighQualityGifs", "memes", "dankmemes"]
    subs = keymap.get(query.lower(), defaults)

    async def try_sub(sub: str) -> Optional[dict]:
        d = await _fetch_json(f"{_MEME_API_BASE}/{sub}")
        if not d or d.get("nsfw"):
            return None
        url = (d.get("url") or "").lower()
        if any(ext in url for ext in (".gif", ".mp4", ".gifv")):
            return d
        return None

    tried = set()
    for _ in range(8):
        sub = random.choice(subs)
        if sub in tried:
            continue
        tried.add(sub)
        item = await try_sub(sub)
        if item:
            e = discord.Embed(title=item.get("title", "GIF"), url=item.get("postLink"), color=0x2b2d31)
            e.set_footer(text=f"r/{item.get('subreddit', sub)}")
            e.set_image(url=item.get("url"))
            await interaction.followup.send(embed=e, ephemeral=SETTINGS.ephemeral)
            return
    await interaction.followup.send(random.choice(_SAFE_FALLBACK_GIFS), ephemeral=SETTINGS.ephemeral)


rbxadmin = app_commands.Group(name="rbxadmin", description="Roblox admin controls")


@rbxadmin.command(name="set_universe", description="Admin: set universe ID")
@admin_only()
@app_commands.describe(universe_id="Numeric universe ID")
async def rbxadmin_set_universe(interaction: discord.Interaction, universe_id: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    uid = _to_int(universe_id)
    if not uid:
        await interaction.followup.send("Invalid universe id.", ephemeral=True)
        return
    bot.universe_id = uid
    bot.root_place_id = None
    await interaction.followup.send(f"Universe set to {uid}.", ephemeral=True)


@rbxadmin.command(name="set_interval", description="Admin: set presence refresh interval (seconds)")
@admin_only()
@app_commands.describe(seconds=">=3 recommended")
async def rbxadmin_set_interval(interaction: discord.Interaction, seconds: app_commands.Range[int, 1, 3600]):
    await interaction.response.defer(ephemeral=True, thinking=True)
    s = max(3, int(seconds))
    presence_loop.change_interval(seconds=s)
    await interaction.followup.send(f"Interval set to {s}s.", ephemeral=True)


@rbxadmin.command(name="set_scan", description="Admin: set scan depth (pages, max items)")
@admin_only()
@app_commands.describe(pages=">=1", max_items=">=100")
async def rbxadmin_set_scan(interaction: discord.Interaction, pages: app_commands.Range[int, 1, 200], max_items: app_commands.Range[int, 100, 20000]):
    await interaction.response.defer(ephemeral=True, thinking=True)
    bot.scan_pages = int(pages)
    bot.scan_limit = int(max_items)
    await interaction.followup.send(f"Scan depth set: pages={bot.scan_pages}, items={bot.scan_limit}.", ephemeral=True)


@rbxadmin.command(name="track_now", description="Admin: force presence update now")
@admin_only()
async def rbxadmin_track_now(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await _presence_once()
        await interaction.followup.send("Presence updated.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Update failed: {e}", ephemeral=True)


bot.tree.add_command(rbxadmin)


@bot.event
async def on_ready():
    if not presence_loop.is_running():
        presence_loop.change_interval(seconds=SETTINGS.interval)
        presence_loop.start()
    print(f"[ready] {bot.user} • commands: {len(bot.tree.get_commands())}")


if __name__ == "__main__":
    bot.run(SETTINGS.token)
