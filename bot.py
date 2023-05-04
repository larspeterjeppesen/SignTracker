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

def get_benched(ID):
  try:
    sql = ''' SELECT name FROM benched WHERE ID = ? '''
    cur = conn.cursor()
    cur.execute(sql, (ID,))
  except Exception as e:
    print(f'exception {e} in method get_benched')
  benched = []  
  res = cur.fetchall()
  for tup in res:
    benched.append(tup[0])
  return benched

def bench(ID, name):
  try:
    sql = ''' INSERT INTO benched VALUE (event_id, name) 
              VALUES (?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (ID, name))
  except sqlite3.IntegrityError as e:
    return False
  except Exception as e:
    print(f'exception {e} in method db_bench')
  return True  

def unbench(ID, name):
  try:
    sql = ''' DELETE FROM benched WHERE event_id = ? AND name = ? '''
    cur = conn.cursor()
    cur.execute(sql, (ID, name))
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



def build_embed(ID, signed, benched, not_signed):
  #Format player lists
  n_signed = len(signed)
  n_benched = len(benched)
  n_not_signed = len(not_signed)
  signed = '\n'.join(signed)
  not_signed = '\n'.join(not_signed)
  benched = '\n'.join(benched)


  embed = discord.Embed(title=f'Tracker for event {ID}',
                        description='',
                        colour=discord.Colour.green())
  
  embed.add_field(name='Signed players', value=signed, inline=False)
  embed.add_field(name='Benched', value=benched, inline=False)
  embed.add_field(name='Not signed players', value=not_signed, inline=True)


  embed.set_footer(text='Contact pixi if this sheet looks broken or incorrent')



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
      signed = get_signs_from_site(event_id)
      not_signed = interaction.channel.members
      for member in not_signed:
        if (signed.__contains__(member.name)):
          not_signed.remove(name)
      
      benched = get_benched(event_id)

      embed = build_embed(event_id, signed, benched, not_signed)

      await interaction.response.send_message(embed=embed)

    @self.tree.command()
    async def bench(interaction: discord.Interaction, player: str, event_id: str):
      ret = bench(event_id, player)
      if (not ret):
        await interaction.response.send_message('Player is already benched', ephemeral=True)
      else:
        await interaction.response.send_message('Player benched', ephemeral=True)

    @self.tree.command()
    async def unbench(interaction: discord.Interaction, player: str, event_id: str):
      ret = unbench(event_id, player)
      if (not ret):
        await interaction.response.send_message('Player was not benched, cannot unbench', ephemeral=True)
      else:
        await interaction.response.send_message('Player benched')


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
conn = create_connection()
client = SignClient()
client.run(TOKEN)






