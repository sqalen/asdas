import discord
import json
import asyncio
import datetime
import time
import random

from discord.ext import commands, tasks


def convert(date):
    pos = ["s", "m", "h", "d"]
    time_dic = {"s": 1, "m": 60, "h": 3600, "d": 3600 *24}
    i = {"s": "Secondes", "m": "Minutes", "h": "Heures", "d": "Jours"}
    unit = date[-1]
    if unit not in pos:
        return -1
    try:
        val = int(date[:-1])

    except:
        return -2

    if val == 1:
        return val * time_dic[unit], i[unit][:-1]
    else:
        return val * time_dic[unit], i[unit]


async def stop_giveaway(self, g_id, data):
    channel = self.bot.get_channel(data["channel_id"])
    giveaway_message = await channel.fetch_message(int(g_id))
    users = await giveaway_message.reactions[0].users().flatten()
    users.pop(users.index(self.bot.user))
    if len(users) < data["winners"]:
        winners_number = len(users)
    else:
        winners_number = data["winners"]

    winners = random.sample(users, winners_number)
    users_mention = []
    for user in winners:
        users_mention.append(user.mention)
    result_embed = discord.Embed(
        title="🎉 {} 🎉".format(data["prize"]),
        color=self.color,
        description="Tebrikler {} Çekilişi Kazandın !".format(", ".join(users_mention))
    ) \
        .set_footer(icon_url=self.bot.user.avatar_url, text="Çekiliş Sonlandırıldı.")
    await giveaway_message.edit(embed=result_embed)
    ghost_ping = await channel.send(", ".join(users_mention))
    await ghost_ping.delete()
    giveaways = json.load(open("cogs/giveaways.json", "r"))
    del giveaways[g_id]
    json.dump(giveaways, open("cogs/giveaways.json", "w"), indent=4)



class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = json.load(open("config.json", "r"))
        self.color = int(self.config["color"], 16) + 0x200
        self.giveaway_task.start()

    def cog_unload(self):
        self.giveaway_task.cancel()

    @tasks.loop(seconds=5)
    async def giveaway_task(self):
        await self.bot.wait_until_ready()
        giveaways = json.load(open("cogs/giveaways.json", "r"))

        if len(giveaways) == 0:
            return

        for giveaway in giveaways:
            data = giveaways[giveaway]
            if int(time.time()) > data["end_time"]:
                await stop_giveaway(self, giveaway, data)


    @commands.command(
        name="giveaway",
        aliases=["gstart"]
    )
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context):
        init = await ctx.send(embed=discord.Embed(
            title="🎉 Yeni Çekiliş ! 🎉",
            description="Çekiliş oluşturma işlemini tamamlamak için lütfen aşağıdaki soruları yanıtlayın",
            color=self.color)
                       .set_footer(icon_url=self.bot.user.avatar_url, text=self.bot.user.name))

        questions = [
            "Çekilişe Bir isim verin. Örnek : (5 Kişiye 100 TL)",
            "Hangi Kanalda Çekiliş Başlatmak İstiyorsun Örnek(#çekiliş) ?",
            "Çekiliş Ne Kadar Sürecek ? Örnek: (1 Gün = 1d | 1 Saat = 1h | 1 Dakika = 1m )",
            "Çekilişin Kaç Kazananı Olacak ?",
            "Çekilişin Embed Mesajını Girin "
        ]

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        index = 1
        answers = []
        question_message = None
        for question in questions:
            embed = discord.Embed(
                title="Giveaway 🎉",
                description=question,
                color=self.color
            ).set_footer(icon_url=self.bot.user.avatar_url, text="Çekiliş !")
            if index == 1:
                question_message = await ctx.send(embed=embed)
            else:
                await question_message.edit(embed=embed)

            try:
                user_response = await self.bot.wait_for("message", timeout=120, check=check)
                await user_response.delete()
            except asyncio.TimeoutError:
                await ctx.send(embed=discord.Embed(
                    title="Error",
                    color=self.color,
                    description="Soruyu Cevaplaman Çok Uzun Sürdü"
                ))
                return
            else:
                answers.append(user_response.content)
                index += 1
        try:
            channel_id = int(answers[1][2:-1])
        except ValueError:
            await ctx.send("Kanal Adını Yanlış Yazdın. Örnek {}.".format(ctx.channel.mention))
            return

        try:
            winners = abs(int(answers[3]))
            if winners == 0:
                await ctx.send("Pozitif bir sayı girmediniz.")
                return
        except ValueError:
            await ctx.send("Bir tam sayı girmediniz.")
            return
        prize = answers[0].title()
        xmessage = answers[4]
        channel = self.bot.get_channel(channel_id)
        converted_time = convert(answers[2])
        if converted_time == -1:
            await ctx.send("Doğru zaman birimini girmediniz (s|m|d|h)")
        elif converted_time == -2:
            await ctx.send("Zaman değeriniz bir tamsayı olmalıdır.")
            return
        await init.delete()
        await question_message.delete()
        giveaway_embed = discord.Embed(
            title="🎉 {} 🎉".format(prize),
            color=self.color,
            description=f'» **{xmessage}**\n'
                        f'» **Çekilişe Katılmak İçin 🎉 Simgesine Tıklayın.**\n'
                        f'» Tarafından Oluşturuldu {ctx.author.mention}\n\n'
                        f'» **{winners}** {"winner" if winners == 1 else "Kişiye"}\n'
        )\
            .set_footer(icon_url=self.bot.user.avatar_url, text="Bitecek")

        giveaway_embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds=converted_time[0])
        giveaway_message = await channel.send(embed=giveaway_embed)
        await giveaway_message.add_reaction("🎉")
        now = int(time.time())
        giveaways = json.load(open("cogs/giveaways.json", "r"))
        data = {
            "prize": prize,
            "host": ctx.author.id,
            "winners": winners,
            "end_time": now + converted_time[0],
            "channel_id": channel.id
        }
        giveaways[str(giveaway_message.id)] = data
        json.dump(giveaways, open("cogs/giveaways.json", "w"), indent=4)

    @commands.command(
        name="gstop",
        aliases=["stop"],
        usage="{giveaway_id}"
    )
    @commands.has_permissions(manage_guild=True)
    async def gstop(self, ctx: commands.Context, message_id):
        await ctx.message.delete()
        giveaways = json.load(open("cogs/giveaways.json", "r"))
        if not message_id in giveaways.keys(): return await ctx.send(
            embed=discord.Embed(title="Error",
                                description="Bu çekiliş ID bulunamadı.",
                                color=self.color))
        await stop_giveaway(self, message_id, giveaways[message_id])

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, (commands.CommandNotFound, discord.HTTPException)):
            return

        if isinstance(error, commands.MissingPermissions):
            return await ctx.send(embed=discord.Embed(
                title="Error",
                description="Bu komutu kullanma izniniz yok.",
                color=self.color))
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(embed=discord.Embed(
                title="Error",
                description=f"Bir argüman sağlamayı unuttunuz, lütfen şöyle yapın: `{ctx.command.name} {ctx.command.usage}`",
                color=self.color))


def setup(bot):
    bot.add_cog(Giveaways(bot))
