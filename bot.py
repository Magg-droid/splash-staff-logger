import discord
import csv
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
from datetime import datetime

from database import conn, cursor

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TIMECLOCK_CHANNEL = int(os.getenv("TIMECLOCK_CHANNEL_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))
MANAGEMENT_CHANNEL = int(os.getenv("MANAGEMENT_CHANNEL"))
OWNER_ROLE = int(os.getenv("OWNER_ROLE_ID"))
MANAGER_ROLE = int(os.getenv("MANAGER_ROLE_ID"))
GENERAL_MANAGER_ROLE = int(
    os.getenv("GENERAL_MANAGER_ROLE_ID")
)

MANAGEMENT_ROLES = [
    OWNER_ROLE,
    MANAGER_ROLE,
    GENERAL_MANAGER_ROLE
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


def is_manager(user):

    return any(
        role.id in MANAGEMENT_ROLES
        for role in user.roles
    )


def get_staff(user):

    cursor.execute(
        "SELECT * FROM staff WHERE user_id=?",
        (user.id,)
    )

    row = cursor.fetchone()

    if row:
        return row

    cursor.execute("""
    INSERT INTO staff
    VALUES(?,?,?,?,?,?)
    """,
    (
        user.id,
        user.name,
        0,
        0,
        None,
        None
    ))

    conn.commit()

    cursor.execute(
        "SELECT * FROM staff WHERE user_id=?",
        (user.id,)
    )

    return cursor.fetchone()


@bot.event
async def on_ready():

    try:

        guild = discord.Object(id=GUILD_ID)

        bot.tree.copy_global_to(
            guild=guild
        )

        synced = await bot.tree.sync(
            guild=guild
        )

        print(
            f"Synced {len(synced)} commands"
        )

    except Exception as e:
        print(e)

    print(f"{bot.user} online")


# ======================
# STAFF STATS
# ======================

@bot.tree.command(
    name="staff",
    description="View staff stats"
)
async def staff(
    interaction: discord.Interaction,
    member: discord.Member
):

    if not is_manager(interaction.user):

        await interaction.response.send_message(
            "Managers only.",
            ephemeral=True
        )
        return

    cursor.execute(
        "SELECT * FROM staff WHERE user_id=?",
        (member.id,)
    )

    row = cursor.fetchone()

    if not row:

        await interaction.response.send_message(
            "No data found.",
            ephemeral=True
        )
        return

    last_active = row[5] or "Never"

    await interaction.response.send_message(
f"""📊 Staff Statistics

Staff: {member.display_name}

Current unpaid PF: {row[2]}
Lifetime PF: {row[3]}
Last active: {last_active}
"""
    )


# ======================
# LEADERBOARD
# ======================

@bot.tree.command(
    name="leaderboard",
    description="Top workers"
)
async def leaderboard(
    interaction: discord.Interaction
):

    if not is_manager(interaction.user):

        await interaction.response.send_message(
            "Managers only.",
            ephemeral=True
        )
        return


    cursor.execute("""
    SELECT user_id,lifetime_pf
    FROM staff
    ORDER BY lifetime_pf DESC
    LIMIT 10
    """)

    rows = cursor.fetchall()

    if not rows:

        await interaction.response.send_message(
            "No data available."
        )
        return


    text = "🏆 Staff Leaderboard\n\n"

    for i, (user_id, lifetime_pf) in enumerate(
        rows,
        start=1
    ):

        member = interaction.guild.get_member(
            user_id
        )

        if member:
            username = member.display_name
        else:
            username = "Unknown User"

        text += (
            f"{i}. {username} — "
            f"{lifetime_pf} PF\n"
        )


    await interaction.response.send_message(
        text
    )


# ======================
# INACTIVE
# ======================

@bot.tree.command(
    name="inactive",
    description="Show inactive staff"
)
async def inactive(
    interaction: discord.Interaction,
    days: int = 0
):

    if not is_manager(interaction.user):

        await interaction.response.send_message(
            "Managers only.",
            ephemeral=True
        )
        return


    cursor.execute("""
    SELECT username,last_active
    FROM staff
    """)

    rows = cursor.fetchall()

    result = []

    now = datetime.now()


    for username, last_active in rows:

        # Never worked since reset
        if not last_active:

            result.append(
                f"{username} — never worked"
            )

            continue


        dt = datetime.fromisoformat(
            last_active
        )

        diff = (
            now - dt
        ).days


        # No number supplied
        if days == 0:

            if diff > 0:

                result.append(
                    f"{username} — last worked {diff} day{'s' if diff != 1 else ''} ago"
                )

        # Optional day filter
        else:

            if diff >= days:

                result.append(
                    f"{username} — last worked {diff} day{'s' if diff != 1 else ''} ago"
                )


    if not result:

        await interaction.response.send_message(
            "✅ No inactive staff found."
        )

        return


    title = "😴 Inactive Staff"

    if days > 0:

        title += f" ({days}+ days)"

    text = title + "\n\n"

    for line in result:

        text += f"{line}\n"


    await interaction.response.send_message(
        text
    )


# ======================
# WIPE DATABASE
# ======================

@bot.tree.command(
    name="wipe_database",
    description="Create report and wipe database"
)
async def wipe_database(
    interaction: discord.Interaction,
    confirm: str
):

    if not is_manager(interaction.user):

        await interaction.response.send_message(
            "Managers only.",
            ephemeral=True
        )
        return


    if confirm.lower() != "yes":

        await interaction.response.send_message(
            "Use: /wipe_database yes",
            ephemeral=True
        )
        return


    cursor.execute("""
    SELECT user_id,
           lifetime_pf,
           last_active
    FROM staff
    """)

    rows = cursor.fetchall()

    total_staff = len(rows)
    total_pf = 0
    inactive = []

    now = datetime.now()

    report = []

    for user_id,lifetime_pf,last_active in rows:

        member = interaction.guild.get_member(
            user_id
        )

        if member:
            username = member.display_name
        else:
            username = "Unknown User"


        total_pf += lifetime_pf

        days_inactive = 0

        if last_active:

            dt=datetime.fromisoformat(
                last_active
            )

            days_inactive=(
                now-dt
            ).days


        report.append(
            (
                username,
                lifetime_pf,
                days_inactive
            )
        )


        if days_inactive > 0:

            inactive.append(
                (
                    username,
                    days_inactive
                )
            )


    report.sort(
        key=lambda x:x[1],
        reverse=True
    )

    inactive.sort(
        key=lambda x:x[1],
        reverse=True
    )


    active_count=(
        total_staff-len(inactive)
    )


    text="📊 Quarterly Staff Report\n"
    text+="━━━━━━━━━━━━━━━━━━\n\n"

    text+="🏆 Top Staff\n\n"

    for i,row in enumerate(
        report[:5],
        start=1
    ):

        text+=(
            f"{i}. "
            f"{row[0]} — "
            f"{row[1]} PF\n"
        )


    text+="\n😴 Inactive Staff\n\n"

    if inactive:

        for user,days in inactive[:10]:

            text+=(
                f"{user} — "
                f"{days} days\n"
            )

    else:

        text+="None\n"


    text+="\n📈 Summary\n\n"

    text+=(
        f"Total Staff: {total_staff}\n"
    )

    text+=(
        f"Active: {active_count}\n"
    )

    text+=(
        f"Inactive: {len(inactive)}\n"
    )

    text+=(
        f"Total PF Completed: {total_pf}\n"
    )

    text+="\n━━━━━━━━━━━━━━━━━━"


    management_channel=bot.get_channel(
        MANAGEMENT_CHANNEL
    )

    if management_channel:

        await management_channel.send(
            text
        )


    cursor.execute(
        "DELETE FROM staff"
    )

    cursor.execute(
        "DELETE FROM payments"
    )

    conn.commit()


    await interaction.response.send_message(
        "✅ Report posted and database wiped."
    )

# ======================
# MESSAGE TRACKING
# ======================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id != TIMECLOCK_CHANNEL:
        return

    content = message.content.upper().strip()

    manager = is_manager(
        message.author
    )

    # Ignore manager advertising
    if manager and content in [
        "PFA",
        "PFC",
        "PFA+C",
        "PFC+A"
    ]:
        return


    # PF tracking
    match = re.match(
        r"^(PFA|PFC)(\d+)(?:\s+.*)?$",
        content
    )

    if match:

        pf_type = match.group(1)

        number = int(
            match.group(2)
        )

        row = get_staff(
            message.author
        )

        current = row[2]

        expected = current + 1

        if number <= current:

            await message.reply(
                f"Expected #{expected} or higher"
            )

            return


        difference = (
            number - current
        )


        cursor.execute("""
        UPDATE staff
        SET current_pf=?,
            lifetime_pf=lifetime_pf+?,
            pf_type=?,
            last_active=?
        WHERE user_id=?
        """,
        (
            number,
            difference,
            pf_type,
            str(datetime.now()),
            message.author.id
        ))

        conn.commit()

        return


    # Payment handling

    paid = re.match(
        r"^>PAID\s+.+<$",
        message.content.strip(),
        re.IGNORECASE
    )

    if paid and manager:

        if not message.mentions:
            return


        staff_user = message.mentions[0]


        cursor.execute(
            "SELECT * FROM staff WHERE user_id=?",
            (staff_user.id,)
        )

        row = cursor.fetchone()

        if not row:
            return


        completed = row[2]


        # Keep payment history silently
        cursor.execute("""
        INSERT INTO payments(
            user_id,
            username,
            completed_pf,
            payment_date
        )
        VALUES(?,?,?,?)
        """,
        (
            row[0],
            row[1],
            completed,
            str(datetime.now())
        ))


        # Reset PF count after payment
        cursor.execute("""
        UPDATE staff
        SET current_pf=0
        WHERE user_id=?
        """,
        (
            row[0],
        ))

        conn.commit()

        return


    await bot.process_commands(message)


bot.run(TOKEN)
