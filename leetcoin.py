"""
Path    addons/source-python/plugins/leetcoin/leetcoin.py
Name    leetcoin
Version 1.0
Author  leetcoin
"""

# ==================================================  ===========================
# >> Imports
# ==================================================  ===========================
import time
import math
import datetime
import threading
from urllib.parse import urlencode
from collections import OrderedDict

try: import re
except ImportError: print ("re Import Error")

try: import hmac
except ImportError: print ("hmac Import Error")

try: import hashlib
except ImportError: print ("hashlib Import Error")

try: import http.client
except ImportError: print ("http.client Import Error")

#import md5

# We import something called a decorator here which we can use to let Source.Python know that we want to listen to the event
from events import Event
from entities.entity import BaseEntity
from entities.helpers import create_entity
from entities.helpers import spawn_entity

# CEngineServer is used to kick players
from engines.server import engine_server

engine = engine_server

try: import json
except ImportError: print ("Json Import Error")

#from tick.repeat import Repeat
#from tick.delays import TickDelays

from listeners.tick import TickRepeat, tick_delays

from messages import SayText2,KeyHintText,HintText

# Import our helper functions
from players.helpers import playerinfo_from_userid, edict_from_userid, index_from_userid, index_from_playerinfo, playerinfo_from_index
from players.entity import PlayerEntity

from filters.players import PlayerIter

from commands.client import ClientCommand, client_command_manager
from commands.say import SayCommand

# Import api client
from .leetcoin_api_client import * 

from colors import RED

# Steam Base ID for Conversion
steamIDBase = 76561197960265728

# instanciate API client
leetcoin_client = LeetCoinAPIClient(url, api_key, shared_secret)

# players requiring activation
pending_activation_player_list = []

round_count = 0
amount_to_pay_winner = 0
paid_list = []
round_won = False

def to_bit(satoshi):
    return str(round(float(satoshi/100),2))

def alive_count():
    print("ALIVE_COUNT")
    count = 0
    for player in PlayerIter(['human', 'alive'], return_types='index'):
        count = count + 1
    return count

def winning_player():
    rPlayer = 0
    if alive_count() == 1: 
        for player in PlayerIter(['human', 'alive'], return_types='userid'):
            rPlayer = player
        if playerinfo_from_userid(rPlayer) in paid_list:
            print("Player paid into the round")
        else: 
            steam64 = convertSteamIDToCommunityID(playerinfo_from_userid(rPlayer).get_networkid_string())
            #leetcoin_client.recordKill(steam64, steam64)
            #leetcoin_client.repeatingServerUpdate()
    return rPlayer

def winning_playerinfo():
    rPlayer = None
    if alive_count() == 1: 
        for player in PlayerIter(['human', 'alive'], return_types='playerinfo'):
            rPlayer = player
    return rPlayer

def collectMoney():
    print("COLLECT_MONEY")
    global round_count
    global paid_list
    count = alive_count()
    increment = leetcoin_client.getIncrementBTC()
    rake = leetcoin_client.getRakePercentage()
    promo = leetcoin_client.isPromo()

    if promo or count == 1:
        print("Promo server, collect nothing")
        tell_all_players("Not enough players, no buy-in collected")
    else:
        for player in PlayerIter(['human', 'alive'], return_types='steamid'):
            steam64 = convertSteamIDToCommunityID(player)
            record = leetcoin_client.recordKill(steam64, steam64)
            if record != "ERROR":
                round_count = round_count + 1
                paid_list.append(steam64)

    set_amount_to_pay()

    if count != 1:
        send_balance()

def set_amount_to_pay():
    global amount_to_pay_winner
    print("AMOUNT TO PAY")
    global round_count
    if leetcoin_client.isPromo():
        amount_to_pay_winner = leetcoin_client.getIncrementBTC()
        print("Amount to pay is Increment because of promo")
    else: 
        amount_to_pay_winner = (leetcoin_client.getIncrementBTC() * round_count) * (.98)
        print("Amount to pay is figured out, round count is: " + str(round_count))

def amount_to_pay():
    global amount_to_pay_winner
    return amount_to_pay_winner



# Create a callback
def my_repeat_callback():
    print(">>>>>>>>>>>>>>>>>>>>>  Repeat")
    
    pop_list = []
    
    for index, pending_activation_player_userid in enumerate(pending_activation_player_list):
        playerinfo = playerinfo_from_userid(pending_activation_player_userid)
        print("my_repeat_callback playerinfo: %s" % playerinfo)
    
        if not playerinfo.get_edict().is_valid():
            print("my_repeat_callback playerinfo edict invalid")
        else:
            steamid = playerinfo.get_networkid_string()
            print("my_repeat_callback player steamid: %s" % steamid)
            
            if not steamid == "BOT":
                print("REAL PLAYER FOUND!")
                steam64 = convertSteamIDToCommunityID(steamid)
                print("steam64: %s" % steam64)
                authorized_active_player = leetcoin_client.authorizeActivatePlayer(steam64, pending_activation_player_userid)
                
            pop_list.append(index)
        
    pop_list.reverse()
    for index_to_remove in pop_list:
        pending_activation_player_list.pop(index_to_remove)
    pass

def submiter_callback():
    print(">>>>>>>>>>>>>>>>>>>>> Repeat Submitter")
    leetcoin_client.repeatingServerUpdate()

# Get the instance of Repeat
my_repeat = TickRepeat(my_repeat_callback)
submit_repeat = TickRepeat(submiter_callback)

# Start the repeat
my_repeat.start(10, 0)
submit_repeat.start(45, 0)

@Event('game_init')
def game_init(game_event):
    print(">>>>>>>>>>>>>>>>>>>>>  game_init")
    pass
    

@Event('round_announce_match_start')
def round_announce_match_start(game_event):
    print(">>>>>>>>>>>>>>>>>>>>>  round_announce_match_start")
    #collectMoney()
    pass   

@Event('round_start')
def round_start(game_event):
    print("Round Start")
    #collectMoney()
    promo = leetcoin_client.isPromo()
    if not promo:
        tell_all_players("Collecting buy-in in 5 seconds")
    tick_delays.delay(5, collectMoney)
    pass
 
@Event('round_end')
def round_end(game_event):
    print(">>>>>>>>>>>>>>>>>>>  Round End")
    promo = leetcoin_client.isPromo()
    if promo:
        leetcoin_client.recordBlankKill()
    leetcoin_client.repeatingServerUpdate()
    global round_count
    round_count = 0
    global paid_list 
    paid_list = []
    global round_won
    round_own = False
    pass   


@Event('player_activate')
def player_activate(game_event):
    """ this includes bots apparently """
    print("Player Connect")
    userid = game_event.get_int('userid')
    print("userid: %s" % userid)
    
    playerinfo = playerinfo_from_userid(userid)
    print("playerinfo: %s" % playerinfo)
    print("playerinfo userid: %s" % playerinfo.get_userid())
    steam64 = convertSteamIDToCommunityID(playerinfo.get_networkid_string())
    print("playerinfo steamid: %s" % steam64)    
    if steam64:
        leetcoin_client.authorizeActivatePlayer(steam64, userid)
        leetcoin_client.recordKill(steam64,steam64)

def check_for_winner():
    count = alive_count()
    global round_count
    global round_won
    if count == 1 and round_count != 1 and not round_won: 
        userid = winning_player()
        amount = amount_to_pay()
        name = playerinfo_from_userid(userid).get_name()
        award = leetcoin_client.requestAward(amount, "Hunger Games Winner", userid)
        tell_winner(winning_playerinfo())
        for player in PlayerIter(['human'], return_types='playerinfo'):
            mes = name + " survived and won " + leetcoin_client.getConvertedAmountValue(convertSteamIDToCommunityID(player.get_networkid_string()), amount)
            SayText2(message="" + mes + "").send(index_from_playerinfo(player))
        print("Winner selected, userid: " + str(userid))
    else:
        print("Alive count at: " + str(count))

@Event('player_disconnect')
def player_disconnect(game_event):
    """ this includes bots apparently """
    print("Player Disconnect")
    userid = game_event.get_int('userid')
    print("userid: %s" % userid)
    playerinfo = playerinfo_from_userid(userid)
    print("playerinfo: %s" % playerinfo)
    steamid = playerinfo.get_networkid_string()
    print("player steamid: %s" % steamid)
    
    if not steamid == "BOT":
        print("REAL PLAYER FOUND!")
        steam64 = convertSteamIDToCommunityID(steamid)
        print("steam64: %s" % steam64)

        tick_delays.delay(5, check_for_winner)

        deactivated_result = leetcoin_client.deactivatePlayer(steam64)
    
@Event('player_death')
def player_death(game_event):
    """ this includes bots apparently """
    print("Player Death")
    # Get the userid from the event
    victim = game_event.get_int('userid')
    attacker = game_event.get_int('attacker')
    print("victim: %s" % victim)
    print("attacker: %s" % attacker)
    
    #victim_edict = edict_from_userid(victim)
    #attacker_edict = edict_from_userid(attacker)
    #print("victim_edict: %s" % victim_edict)
    #print("attacker_edict: %s" % attacker_edict)
    
    # Get the CPlayerInfo instance from the userid
    victimplayerinfo = playerinfo_from_userid(victim)
    attackerplayerinfo = playerinfo_from_userid(attacker)
    print("victimplayerinfo: %s" % victimplayerinfo)
    print("attackerplayerinfo: %s" % attackerplayerinfo)
    # And finally get the player's name 
    #victimname = victimplayerinfo.get_name()
    #attackername = attackerplayerinfo.get_name()
    #print("victimname: %s" % victimname)
    #print("attackername: %s" % attackername)
    
    # Get the index of the player
    victimindex = index_from_userid(victim)
    attackerindex = index_from_userid(attacker)
    print("victimindex: %s" % victimindex)
    print("attackerindex: %s" % attackerindex)
    
    print("victim_is_fake_client: %s" % victimplayerinfo.is_fake_client())
    print("attacker_is_fake_client: %s" % attackerplayerinfo.is_fake_client())
    
    victim_steamid = victimplayerinfo.get_networkid_string()
    attacker_steamid = attackerplayerinfo.get_networkid_string()
    
    if not victimplayerinfo.is_fake_client() and not attackerplayerinfo.is_fake_client():
        count = alive_count()
        global round_count
        global round_won
        if count == 1 and round_count != 1: 
            userid = winning_player()
            amount = amount_to_pay()
            name = playerinfo_from_userid(userid).get_name()
            award = leetcoin_client.requestAward(amount, "Hunger Games Winner", userid)
            tell_winner(winning_playerinfo())
            for player in PlayerIter(['human'], return_types='playerinfo'):
                mes = name + " survived and won " + leetcoin_client.getConvertedAmountValue(convertSteamIDToCommunityID(player.get_networkid_string()), amount)
                SayText2(message="" + mes + "").send(index_from_playerinfo(player))
            print("Winner selected, userid: " + str(userid))
            round_won = True
            #leetcoin_client.submit_match_results_blank()
        else:
            print("Alive count at: " + str(count))


    return
  


# Covnert Steam ID to Steam64
def convertSteamIDToCommunityID(steamID):
    print("[1337] convertSteamIDToCommunityID")
    print("steamID: %s" %steamID)
    if steamID == "BOT":
        return False
    steamIDParts = re.split(":", steamID)
    print("steamIDParts: %s" %steamIDParts)
    communityID = int(steamIDParts[2]) * 2
    if steamIDParts[1] == "1":
        communityID += 1
    communityID += steamIDBase
    return communityID
    
                
def doKick(userid, message):
    try:
        print("[1337] [doKick] player: %s" %userid)
    except:
        print("[1337] PLAYER NOT FOUND")
    
    try:
        engine.server_command('kickid %s %s;' % (int(userid), message))
    except:
        print("[1337] KICK FAILURE for user: %s" %userid)
        
def calculate_elo_rank(player_a_rank=1600, player_b_rank=1600, penalize_loser=True):
    winner_rank, loser_rank = player_a_rank, player_b_rank
    rank_diff = winner_rank - loser_rank
    exp = (rank_diff * -1) / 400
    odds = 1 / (1 + math.pow(10, exp))
    if winner_rank < 2100:
        k = 32
    elif winner_rank >= 2100 and winner_rank < 2400:
        k = 24
    else:
        k = 16
    new_winner_rank = round(winner_rank + (k * (1 - odds)))
    if penalize_loser:
        new_rank_diff = new_winner_rank - winner_rank
        new_loser_rank = loser_rank - new_rank_diff
    else:
        new_loser_rank = loser_rank
    if new_loser_rank < 1:
        new_loser_rank = 1
    return (new_winner_rank, new_loser_rank)

@Event('other_death')
def other_death(game_event):
    """Fired when a non-player entity is dying."""

    # Make sure the entity was a chicken...
    if game_event.get_string('othertype') != 'chicken':
        return
    print("CHICKEN DIED")
    # Get the attacker's userid...
    userid = game_event.get_int('attacker')
    
    # Make sure the attacker was a player...
    if not userid:
        return
    
    # Ask for reward 
    award = leetcoin_client.requestAward(100, "Chicken killa", userid)
    # Get a PlayerEntity instance of the attacker...
    attacker = PlayerEntity(index_from_userid(game_event.get_int('attacker')))
    # Display a message...
    SayText2(message='{0} killed a chicken and had a chance to earn 1 Bit!'.format(
        attacker.name)).send()
    

@Event('player_say')
def player_say(game_event):
    """Fired every time a player is typing something."""
    # Make sure the typed text was "/chicken"...
    if game_event.get_string('text') != '/chicken':
        return

    # Create a chicken entity...
    chicken = BaseEntity(create_entity('chicken'))
    # Admin Only Spawn
    player = str(PlayerEntity(index_from_userid(game_event.get_int('userid'))).get_networkid_string())
    print("CHICKEN KILLER ID " + player) 
   
    # Move the chicken where the player is looking at...
    chicken.origin = PlayerEntity(index_from_userid(game_event.get_int(
        'userid'))).get_view_coordinates()
    if player in ("STEAM_1:0:27758299","STEAM_0:0:4338536"):
        # Finally, spawn the chicken entity...
        spawn_entity(chicken.index)

def send_balance():
    promo = leetcoin_client.isPromo()
    increment = leetcoin_client.getIncrementBTC()
    if promo:
        increment = 0
    amount = amount_to_pay()
    for player in PlayerIter(['human', 'alive'], return_types='playerinfo'):
        balance = leetcoin_client.getPlayerBalance(convertSteamIDToCommunityID(player.get_networkid_string()))
        mes = "Round Buy in: -" + leetcoin_client.getConvertedAmountValue(convertSteamIDToCommunityID(player.get_networkid_string()), increment)
        mes2 = "Updated " + balance + "" # balance
        mes3 = "Last one to survive wins the pot! (+" + leetcoin_client.getConvertedAmountValue(convertSteamIDToCommunityID(player.get_networkid_string()), amount) + " )" # amount
        SayText2(message="" + mes + "").send(index_from_playerinfo(player))
        SayText2(message="" + mes2 + "").send(index_from_playerinfo(player))
        SayText2(message="" + mes3 + "").send(index_from_playerinfo(player))

def tell_winner(playerinfo):
    amount = amount_to_pay()
    balance = leetcoin_client.getPlayerBalance(convertSteamIDToCommunityID(playerinfo.get_networkid_string()))
    mes = "You won " + leetcoin_client.getConvertedAmountValue(convertSteamIDToCommunityID(playerinfo.get_networkid_string()), amount)
    #mes2 = "Updated " + balance
    SayText2(message="" + mes + "").send(index_from_playerinfo(playerinfo))
    #SayText2(message="" + mes2 + "").send(index_from_playerinfo(playerinfo))

def tell_all_players(mes):
    for player in PlayerIter(['human'], return_types='playerinfo'):
        SayText2(message="" + mes + "").send(index_from_playerinfo(player))

@SayCommand("balance")
def saycommand_test(command, index, team_only): #playerinfo, teamonly, command
    playerinfo = playerinfo_from_index(index)
    balance = leetcoin_client.getPlayerBalance(convertSteamIDToCommunityID(playerinfo.get_networkid_string()))
    SayText2(message="" + balance + "").send(index)

@SayCommand("rank")
def saycommand_rank(command, index, team_only):
    playerinfo = playerinfo_from_index(index)
    rank = leetcoin_client.getPlayerRank(convertSteamIDToCommunityID(playerinfo.get_networkid_string()))
    SayText2(message="" + rank + "").send(index)

@SayCommand("pot")
def saycommand_pot(command, index, team_only):
    pot = amount_to_pay()
    mes = "Pot amount: " + str(pot)
    SayText2(message="" + mes + "").send(index)

@SayCommand("test")
def saycommand_say(command, index, team_only):
    global round_count
    aliveCount = alive_count()
    amount = amount_to_pay()
    print("Alive Count: " + str(aliveCount) + "\nRound Count: " + str(round_count))
    send_balance()