import sqlite3
from typing import List
import discord
from discord import app_commands
from datetime import datetime

#Local data
from settings import DISCORD_TOKEN, GUILD_ID, DB_PATH
from game_data import WOTLK_CLASSES
from selectViews import *

from db_interface import *

TEST_GUILD = discord.Object(id=GUILD_ID)
COLOUR_THEME = discord.Colour.green()

def getdatetime():
  return datetime.now().strftime('%d/%m/%Y %H:%M:%S')


#EventModal is a popup window that may be called using a button (and maybe other things)
#Example usage:
#modal = EventModal()
#await interaction.response.send_modal(modal_query)
#await modal_query.wait()
class EventModal(discord.ui.Modal, title="Event information"):

  input1 = discord.ui.TextInput(
    custom_id = 'field1',
    style=discord.TextStyle.short,
    label='Event Name:',
    required=False,
    max_length=128,
    placeholder='Write some text'
  )

  # Edit the field the modal is concerned with
  async def on_submit(self, interaction: discord.Interaction):
    field1 = interaction.data['components'][0]['components'][0]['value']
#    field2 = interaction.data['components'][1]['components'][0]['value']
    #embed_fields = interaction.message.embeds[0].fields
    #print(embed_fields)  
    embed = EventEmbed(lvl_req=field1)
    await interaction.response.edit_message(embed=embed)

  async def on_error(self, interaction: discord.Interaction, error):
    print(error)

def wotlk_class_entries(players):
  d = {}
  d['Warrior'] = ''
  d['Rogue'] = ''
  d['Shaman'] = ''
  d['Hunter'] = ''
  d['Paladin'] = ''
  d['Warlock'] = ''
  d['Mage'] = ''
  d['Druid'] = ''
  d['Priest'] = ''
  d['Deathknight'] = ''
  for i in range(len(players)):
    # players[i][4] is supposed to be the class of the character
    # players[i][2] is supposed to be the name of the character
    d[players[i][1]] += f'\n{players[i][0]}'
  return d
  

def get_event_embed(event_id):
  fields = db_get_event(conn,event_id) 
  players = db_get_event_characters(conn,event_id, fields['game']) 

  #create embed
  embed = discord.Embed(title=fields['title'], 
                        description=fields['description'], 
                        colour=COLOUR_THEME)
  embed.set_author(name=f"{fields['creator']}")
  #embed.set_thumbnail(url=f'{pfp}')
  embed.add_field(name='Time', value=f"{fields['date_deadline']}", inline=False)
  
  if fields['players_min']:
    embed.add_field(name=f'Minimum required players', value=f"{fields['players_min']}", inline=True)
  if fields['players_max']:
    embed.add_field(name=f'Maximum players', value=f"{fields['players_max']}",inline=True)

  match fields['game']:
    case 'wotlk':
      game_fields = db_get_event_wotlk(conn,event_id)
      classes = wotlk_class_entries(players)
      embed.add_field(name='', value='', inline=False) 
      for key in classes:
        if classes[key] != '':
          embed.add_field(name=key, value=classes[key])


    case _:
      game_fields = None
      embed.add_field(name='Signups', value=players, inline=False)
      #TODO pull character names out of players into a list
      #the line below may be incorrect
      characters = '\n'.join(player[2] for player in players)


 

  #Bottom line
  embed.set_footer(text=f"Created by {fields['creator']} on {fields['date_created']}")

  return embed



class MyClient(discord.Client):
    def __init__(self):

        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.prepare_client()


    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=TEST_GUILD)
        await self.tree.sync(guild=TEST_GUILD)


    def prepare_client(self):
      @self.event
      async def on_ready():
        print(f'Logged in as user: {self.user}')
        print('-------/n')


      @self.tree.command()
      async def getevent(interaction: discord.Interaction, event_id: int):
        embed = get_event_embed(event_id)
        view = ButtonView(event_id)
        await interaction.response.send_message(embed=embed,view=view)

      @self.tree.command()
      async def print_user_info(interaction: discord.Interaction):
        print(interaction.user)
        print(interaction.user.id)
        print(type(interaction.user))


      @self.tree.command()
      async def register_user(interaction: discord.Interaction):
        time = getdatetime()
        message = db_insert_user(conn,interaction,time=time,create_event=1,sign_event=1)
        if message == None:
          message = 'User registered'
        
        await interaction.response.send_message(message)

      @self.tree.command()
      async def remove_user(interaction: discord.Interaction):
        message = db_remove_user(conn,interaction)
        if message == None:
          message = 'User deleted from database'
        await interaction.response.send_message(message)

      @self.tree.command()
      async def register_character(interaction: discord.Interaction, character_name: str, game: str): 

        #TODO:
        #Create a view containing a dropdown listing classes in selected game
        #When selecting a class, add a second drop down listing available specs for
        #selected class
        #When selection is made from the dropdowns, add a button to finalize registration
        

        view = CharCreationView(character_name, game)
        print(view)
        #message = db_register_character(conn,interaction, character_name)
        message = f'Creation for character {character_name}'
        await interaction.response.send_message(message, view=view)



      @self.tree.command()
      async def insert_event(interaction: discord.Interaction,
                             title: str,
                             description: str,
                             date_deadline: str,
                             game: str,
                             players_min: str,
                             players_max: str
                             ):
                             
        args = {}
        args['title'] = title
        args['description'] = description
        args['date_deadline'] = date_deadline
        args['game'] = game
        args['players_min'] = players_min
        args['players_max'] = players_max

        args['date_created'] = getdatetime()
        args['creator'] = interaction.user.display_name
        args['guild_id'] = interaction.guild.id
        
        (event_id, response) = db_create_event(conn,interaction, args)
        
        if event_id == -1:
          await interaction.response.send_message(response)
       
        else:
          embed = get_event_embed(event_id)
          view = ButtonView(event_id)
          await interaction.response.send_message(embed=embed,view=view)              


conn = create_connection(DB_PATH)

client = MyClient()
client.run(DISCORD_TOKEN)
