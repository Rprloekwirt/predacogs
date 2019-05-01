import discord

from redbot.core.utils.chat_formatting import humanize_timedelta

import aiohttp

from datetime import datetime
from typing import Optional

SPACE_X_API_BASE_URL = "https://api.spacexdata.com/v3/"


class Core:
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def _unix_convert(self, timestamp: int):
        """Convert a unix timestamp to a readable datetime."""
        try:
            given = timestamp[: timestamp.find(".")] if "." in str(timestamp) else timestamp
            convert = datetime.utcfromtimestamp(int(given)).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError):
            raise ValueError(f"{given} is not a valid timestamp.")
        b = datetime.fromtimestamp(int(given))
        curr = datetime.fromtimestamp(int(datetime.now().timestamp()))
        secs = str((curr - b).total_seconds())
        seconds = secs[1:][:-2] if "-" in secs else secs[:-2] if ".0" in secs else secs
        delta = humanize_timedelta(seconds=int(seconds))
        return convert, delta

    async def _get_data(self, ctx, endpoint: Optional[str] = ""):
        """Get data from SpaceX API."""
        async with self.session.get(SPACE_X_API_BASE_URL + endpoint) as resp:
            if resp.status == 404:
                await ctx.send("It doesn't seem to be a valid request.")
                return None
            elif resp.status != 200:
                await ctx.send(
                    "Error when trying to get SpaceX API. Error code: `{}`".format(resp.status)
                )
                return None
            data = await resp.json()
            return data

    async def _about(self, ctx, version=None):
        async with ctx.typing():
            data = await self._get_data(ctx)
            description = data["description"]
            docs = data["docs"]
            project_link = data["project_link"]
            if data is None:
                description = (
                    "Open Source REST API for rocket, core, capsule, pad, and launch data, "
                    "created and maintained by the developers of the r/SpaceX organization"
                )
                docs = "https://documenter.getpostman.com/view/2025350/RWaEzAiG"
                project_link = "https://github.com/r-spacex/SpaceX-API"
                return
            try:
                title_api = "About SpaceX-API:\n"
                title_cog = "About this cog:\n"
                desc_api = (
                    description + "\n**[Docs]({docs})** • **[Project Link]({project})**"
                ).format(docs=docs, project=project_link)
                desc_cog = "Cog version: " + version
                em = discord.Embed(color=await ctx.embed_colour())
                em.add_field(name=title_api, value=desc_api)
                em.add_field(name=title_cog, value=desc_cog)
                return await ctx.send(embed=em)
            except discord.errors.Forbidden:
                msg = (
                    f"**{title_api}**\n"
                    + description
                    + "\n\nDocs:\n"
                    + docs
                    + "\nProject Link:\n"
                    + project_link
                    + f"\n\n**{title_cog}**\n"
                    + "Cog version: "
                    + version
                )
                return await ctx.send(msg)

    async def _roadster_texts(self, data):
        date, delta = await self._unix_convert(data["launch_date_unix"])
        roadster_stats_kwargs = {
            "launch_date": date,
            "ago": delta[:-31],
            "mass_kg": data["launch_mass_kg"],
            "mass_lbs": data["launch_mass_lbs"],
            "speed_km": round(data["speed_kph"], 2),
            "speed_mph": round(data["speed_mph"], 2),
            "e_distance_km": round(data["earth_distance_km"], 2),
            "e_distance_mi": round(data["earth_distance_mi"], 2),
            "m_distance_km": round(data["mars_distance_km"], 2),
            "m_distance_mi": round(data["mars_distance_mi"], 2),
        }
        roadster_stats = (
            "Launch date: **{launch_date} {ago} ago**\n"
            "Launch mass: **{mass_kg:,} kg / {mass_lbs:,} lbs**\n"
            "Actual speed: **{speed_km:,} km/h / {speed_mph:,} mph**\n"
            "Earth distance: **{e_distance_km:,} km / {e_distance_mi:,} mi**\n"
            "Mars distance: **{m_distance_km:,} km / {m_distance_mi:,} mi**\n"
        ).format(**roadster_stats_kwargs)
        return roadster_stats

    async def _rockets_texts(self, data):
        base_stats_kwargs = {
            "first_flight": data["first_flight"],
            "active": "Yes" if data["active"] == True else "No",
            "stages": data["stages"],
            "l_legs": data["landing_legs"]["number"],
            "success_rate": data["success_rate_pct"],
            "cost": data["cost_per_launch"],
            "m_height": round(data["height"]["meters"], 2),
            "f_height": round(data["height"]["feet"], 2),
            "m_diam": round(data["diameter"]["meters"], 2),
            "f_diam": round(data["diameter"]["feet"], 2),
            "kg_mass": round(data["mass"]["kg"], 2),
            "lb_mass": round(data["mass"]["lb"], 2),
            "engines": data["engines"]["number"],
            "e_type": data["engines"]["type"],
            "e_version": data["engines"]["version"],
        }
        base_stats = (
            "First flight: **{first_flight}**\n"
            "Active: **{active}**\n"
            "Stages: **{stages:,}**\n"
            "Landing legs: **{l_legs:,}**\n"
            "Success rate: **{success_rate}%**\n"
            "Cost per launch: **{cost:,}$**\n"
            "Height: **{m_height:,} m / {f_height:,} f**\n"
            "Diameter: **{m_diam:,} m / {f_diam:,} f**\n"
            "Mass: **{kg_mass:,} kg / {lb_mass:,} lbs**\n"
            "Engines: **{engines} {e_type} {e_version}**"
        ).format(**base_stats_kwargs)
        stages_stats_kwargs = {
            "fi_reusable": "Yes" if data["first_stage"]["reusable"] == True else "No",
            "fi_engines": data["first_stage"]["engines"],
            "fi_fuel_amount": data["first_stage"]["fuel_amount_tons"],
            "fi_burn_time": "N/A"
            if data["first_stage"]["burn_time_sec"] == None
            else data["first_stage"]["burn_time_sec"],
            "sec_reusable": "Yes" if data["second_stage"]["reusable"] == True else "No",
            "sec_engines": data["second_stage"]["engines"],
            "sec_fuel_amount": data["second_stage"]["fuel_amount_tons"],
            "sec_burn_time": "N/A"
            if data["second_stage"]["burn_time_sec"] == None
            else data["second_stage"]["burn_time_sec"],
        }
        stages_stats = (
            "***First stage:***\n"
            "Reusable: **{fi_reusable}**\n"
            "Engines: **{fi_engines}**\n"
            "Fuel amount: **{fi_fuel_amount} tons**\n"
            "Burn time: **{fi_burn_time} secs**\n"
            "***Second stage:***\n"
            "Reusable: **{sec_reusable}**\n"
            "Engines: **{sec_engines}**\n"
            "Fuel amount: **{sec_fuel_amount} tons**\n"
            "Burn time: **{sec_burn_time} secs**\n"
        ).format(**stages_stats_kwargs)
        payload_weights_stats = ""
        for p in data["payload_weights"]:
            payload_weights_stats += (
                "Name: **{p_name}**\n" "Weight: **{kg_mass:,} kg / {lb_mass:,} lbs**\n"
            ).format(p_name=p["name"], kg_mass=p["kg"], lb_mass=p["lb"])
        engines_stats_kwargs = {
            "number": data["engines"]["number"],
            "type": data["engines"]["type"],
            "version": "None" if data["engines"]["version"] == "" else data["engines"]["version"],
            "layout": data["engines"]["layout"],
            "p_1": data["engines"]["propellant_1"],
            "p_2": data["engines"]["propellant_2"],
        }
        engines_stats = (
            "Number: **{number:,}**\n"
            "Type: **{type}**\n"
            "Version: **{version}**\n"
            "Layout: **{layout}**\n"
            "Propellants: **{p_1} and {p_2}**"
        ).format(**engines_stats_kwargs)
        return base_stats, stages_stats, payload_weights_stats, engines_stats

    def __unload(self):
        self.bot.loop.create_task(self.session.close())
