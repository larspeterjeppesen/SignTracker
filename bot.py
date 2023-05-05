import sqlite3
import discord
import requests
import os
from dotenv import load_dotenv


def create_connection():
  conn = None
  try:
    conn = sqlite3.connect('tracker.db')
  except Error as e:
    print(e)
  return conn

def del_tracker(event_id):
  try:
    sql = ''' DELETE FROM trackers WHERE event_id = ? '''
    cur = conn.cursor()
    cur.execute(sql, (event_id,))
    conn.commit()
  except Exception as e:
    print(f'exception {e} in method del_tracker')
  if (cur.rowcount == 0):
    return False
  return True

def get_tracker_message(event_id):
  try:
    sql = ''' SELECT message_id FROM trackers WHERE event_id = ? '''
    cur = conn.cursor()
    cur.execute(sql, (event_id,))
  except Exception as e:
    print(f'exception {e} in method tracker_exists')
  res = cur.fetchall()
  if (len(res) == 0):
    return None
  return res[0][0]

def store_tracker_message(event_id, message_id):
  try:
    sql = ''' INSERT INTO trackers (event_id, message_id)
              VALUES (?,?) ''' 
    cur = conn.cursor()
    cur.execute(sql, (event_id, message_id))
    conn.commit()
  except sqlite3.IntegrityError as e:
    return False
  except Exception as e:
    print(f'exception {e} in method store_tracker_message')
  return True

def get_benched(ID):
  try:
    sql = ''' SELECT name FROM benched WHERE event_id = ? '''
    cur = conn.cursor()
    cur.execute(sql, (ID,))
  except Exception as e:
    print(f'exception {e} in method get_benched')
  benched = []  
  res = cur.fetchall()
  for tup in res:
    benched.append(tup[0])
  return benched

def db_bench(ID, name):
  try:
    sql = ''' INSERT INTO benched (event_id, name) 
              VALUES (?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (ID, name))
    conn.commit()
  except sqlite3.IntegrityError as e:
    return False
  except Exception as e:
    print(f'exception {e} in method db_bench')
  return True  

def db_unbench(ID, name):
  try:
    sql = ''' DELETE FROM benched WHERE event_id = ? AND name = ? '''
    cur = conn.cursor()
    cur.execute(sql, (ID, name))
    conn.commit()
  except Exception as e:
    print('exception {e} in method db_unbench')
  if cur.rowcount == 0:
    return False
  return True


def get_signs_from_site(ID):
  #TODO: check for invalid website
  URL = f'https://raid-helper.dev/api/event/{ID}'
  j = requests.get(URL).json()
  signs = {}
  signs['Absent'] = []
  signs['Available'] = []
  for i in range(len(j['signups'])):
    if (j['signups'][i]['role'] == 'Absence'):
      signs['Absent'].append(j['signups'][i]['name'])
    else:
      signs['Available'].append(j['signups'][i]['name'])
  return signs


async def update_tracker_message(interaction, event_id):
  message_id = get_tracker_message(event_id)
  message = await interaction.channel.fetch_message(message_id)
  embed = build_embed(interaction, event_id)
  await message.edit(content=message.content, embed=embed)

def build_embed(interaction, event_id):
  #Build player lists 
  signed = get_signs_from_site(event_id)
  benched = get_benched(event_id)
  not_signed_members = interaction.channel.members
  not_signed = []
  for member in not_signed_members:
    if (not signed.__contains__(member.name) and not member.bot):
      not_signed.append(member.name)
 
  for name in benched:
    if (name in signed):
      signed.remove(name)
 
 #Format player lists
  n_available = len(signed['Available'])
  available = '\n'.join(signed['Available'])
  n_absent = len(signed['Absent'])
  absent = '\n'.join(signed['Absent'])
  n_benched = len(benched)
  benched = '\n'.join(benched)
  n_not_signed = len(not_signed)
  not_signed = '\n'.join(not_signed)

  embed = discord.Embed(title=f'Tracker for event {event_id}',
                        description='',
                        colour=discord.Colour.green())
  
  embed.add_field(name=f'Players available ({n_available})', value=available, inline=True)
  embed.add_field(name=f'Benched ({n_benched})', value=benched, inline=True)
  embed.add_field(name=' ', value=' ', inline=False)
  embed.add_field(name=f'Absent ({n_absent})', value=absent, inline = True) 
  embed.add_field(name=f'Not signed players ({n_not_signed})', value=not_signed, inline=True)

  embed.set_footer(text='Contact pixi if this sheet looks broken or incorrent')

  return embed

class SignClient(discord.Client):
  def __init__(self):
    intents = discord.Intents.default()
    intents.members = True
    super().__init__(intents=intents)
    self.tree = discord.app_commands.CommandTree(self) 
    self.prepare_client()


  async def setup_hook(self):
    guild_obj = discord.Object(id=GUILD_ID)
    self.tree.copy_global_to(guild=guild_obj)
    await self.tree.sync(guild=guild_obj)
    print('ran setup_hook')


  def prepare_client(self):
    @self.event
    async def on_ready():
      print(f'Logged in as user: {self.user}')
      print('------\n')

    @self.tree.command()
    async def track(interaction: discord.Interaction, event_id: str):
      if (get_tracker_message(event_id) != None):
        await interaction.response.send_message('Event is already being tracked')
        return
       
      embed = build_embed(interaction, event_id)
      response = f'tracking event {event_id}'
      await interaction.response.send_message(content=response, embed=embed)
      message = await interaction.original_response()
      store_tracker_message(event_id, message.id)

    @self.tree.command()
    async def untrack(interaction: discord.Interaction, event_id: str, remove_benches: str):
      ret = del_tracker(event_id)
      response = 'Tracker not found, can\t delete.'
      if (ret):
        response = 'Tracker deleted'
      await interaction.response.send_message(response)
        
    @self.tree.command()
    async def bench(interaction: discord.Interaction, player: str, event_id: str):
      name = None
      for member in interaction.channel.members:
        if (member.name.lower() == player.lower()):
          name = member.name
      if (name == None):
        await interaction.response.send_message(f'{player} not found.', ephemeral=True)
      else:
        ret = db_bench(event_id, name)
        if (not ret):
          await interaction.response.send_message(f'{player} is already benched.', ephemeral=True)
        else:
          await update_tracker_message(interaction, event_id)
          await interaction.response.send_message(f'{player} benched.', ephemeral=True)

    @self.tree.command()
    async def unbench(interaction: discord.Interaction, player: str, event_id: str):
      name = None
      for member in interaction.channel.members:
        if (member.name.lower() == player):
          name = member.name
      if (name == None):
        print('success')
        #await interaction.response.send_message(f'{player} not recognized.', ephemeral=True)
    
      ret = db_unbench(event_id, name)
      if (not ret):
        await interaction.response.send_message(f'{player} is not benched, cannot unbench.', ephemeral=True)
      else:
        await update_tracker_message(interaction, event_id)
        await interaction.response.send_message(f'{player} unbenched.', ephemeral=True)


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
conn = create_connection()
client = SignClient()
client.run(TOKEN)






