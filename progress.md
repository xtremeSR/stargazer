"{"id":"showdown","host":"sim2.psim.us","port":443,"httpport":8000,"altport":80,"registered":true}

""/showdown""

day 2 got the websocket communicating with the showdown server

We have to learn the policy, which is a joint distribution of the
game state and player actions. The problem with learning every element
of this joint table is that there would be too many parameters involved.
The number of game state x the set of all actions taken.

The best method is to make a model distribtution for the policy whose
parameters can be learned by maximum liklihood or MAP.

["|/utm null"]
["|/search gen7randombattle"]
|updatesearch|{"searching":["gen7randombattle"],"games":null}
|updatesearch|{"searching":[],"games":{"battle-gen7randombattle-636348764":"[Gen 7] Random Battle*"}}
>battle-gen7randombattle-636348764↵|init|battle↵|title|soohamr vs. rafael789↵|j|soohamr
>battle-gen7randombattle-636348764↵|request|
>battle-gen7randombattle-636348764↵↵|J|rafael789
>battle-gen7randombattle-636348764↵↵|player|p1|soohamr|1↵|teamsize|p1|6

>battle-gen7randombattle-636348764↵|request|{"active":[{"moves":[{"move":"Roost","id":"roost","pp":16,"maxpp":16,"target":"self","disabled":false},{"move":"Will-O-Wisp","id":"willowisp","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Flare Blitz","id":"flareblitz","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Dragon Claw","id":"dragonclaw","pp":24,"maxpp":24,"target":"normal","disabled":false}],"canMegaEvo":true}],"side":{"name":"soohamr","id":"p1","pokemon":[{"ident":"p1: Charizard","details":"Charizard, L75, M","condition":"241/241","active":true,"stats":{"atk":170,"def":161,"spa":207,"spd":171,"spe":194},"moves":["roost","willowisp","flareblitz","dragonclaw"],"baseAbility":"blaze","item":"charizarditex","pokeball":"pokeball","ability":"blaze"},{"ident":"p1: Durant","details":"Durant, L77, F","condition":"216/216","active":false,"stats":{"atk":212,"def":217,"spa":118,"spd":118,"spe":212},"moves":["batonpass","honeclaws","superpower","ironhead"],"baseAbility":"hustle","item":"leftovers","pokeball":"pokeball","ability":"hustle"},{"ident":"p1: Regigigas","details":"Regigigas, L83","condition":"318/318","active":false,"stats":{"atk":313,"def":230,"spa":180,"spd":230,"spe":214},"moves":["return","confuseray","drainpunch","substitute"],"baseAbility":"slowstart","item":"leftovers","pokeball":"pokeball","ability":"slowstart"},{"ident":"p1: Beartic","details":"Beartic, L83, F","condition":"293/293","active":false,"stats":{"atk":263,"def":180,"spa":164,"spd":180,"spe":131},"moves":["aquajet","swordsdance","iciclecrash","nightslash"],"baseAbility":"swiftswim","item":"lifeorb","pokeball":"pokeball","ability":"swiftswim"},{"ident":"p1: Hariyama","details":"Hariyama, L82, F","condition":"370/370","active":false,"stats":{"atk":244,"def":146,"spa":113,"spd":146,"spe":129},"moves":["bulkup","stoneedge","knockoff","closecombat"],"baseAbility":"thickfat","item":"lifeorb","pokeball":"pokeball","ability":"thickfat"},{"ident":"p1: Magearna","details":"Magearna, L75","condition":"244/244","active":false,"stats":{"atk":147,"def":216,"spa":239,"spd":216,"spe":141},"moves":["aurasphere","fleurcannon","icebeam","thunderbolt"],"baseAbility":"soulheart","item":"choicescarf","pokeball":"pokeball","ability":"soulheart"}]},"rqid":2}

>battle-gen7randombattle-636348764↵↵|player|p2|rafael789|25↵|teamsize|p2|6↵|gametype|singles↵|gen|7↵|tier|[Gen 7] Random Battle↵|rated↵|seed|↵|rule|Sleep Clause Mod: Limit one foe put to sleep↵|rule|HP Percentage Mod: HP is shown in percentages↵|↵|start↵|switch|p1a: Charizard|Charizard, L75, M|241/241↵|switch|p2a: Rotom|Rotom-Fan, L83|100/100↵|-item|p2a: Rotom|Air Balloon↵|turn|1

>battle-gen7randombattle-636348764↵↵|-message|rafael789 forfeited.
>battle-gen7randombattle-636348764↵|askreg|soohamr
>battle-gen7randombattle-636348764↵↵|↵|win|soohamr
>battle-gen7randombattle-636348764↵||Ladder updating...
|updatesearch|{"searching":[],"games":null}
>battle-gen7randombattle-636348764↵↵|L|rafael789
>battle-gen7randombattle-636348764↵↵|raw|soohamr's rating: 1026 &rarr; <strong>1068</strong><br />(+42 for winning)↵|raw|rafael789's rating: 1082 &rarr; <strong>1056</strong><br />(-26 for losing)
/leave battle-gen7randombattle-636348764
>battle-gen7randombattle-636348764↵|deinit

"|/leave lobby"
a["|deinit"]



|/utm null
|/search gen7randombattle
battle-gen7randombattle-636352623|/choose move 4|3
battle-gen7randombattle-636352623|/choose switch 6|5
>battle-gen7randombattle-636352623↵|request|{"active":[{"moves":[{"move":"Hidden Power Ground","id":"hiddenpower","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Sludge Wave","id":"sludgewave","pp":15,"maxpp":16,"target":"allAdjacent","disabled":false},{"move":"Nasty Plot","id":"nastyplot","pp":32,"maxpp":32,"target":"self","disabled":false},{"move":"Fire Blast","id":"fireblast","pp":8,"maxpp":8,"target":"normal","disabled":false}]}],"side":{"name":"soohamr","id":"p2","pokemon":[{"ident":"p2: Salazzle","details":"Salazzle, L79, F","condition":"237/237","active":true,"stats":{"atk":106,"def":140,"spa":221,"spd":140,"spe":230},"moves":["hiddenpowerground60","sludgewave","nastyplot","fireblast"],"baseAbility":"corrosion","item":"airballoon","pokeball":"pokeball","ability":"corrosion"},{"ident":"p2: Minun","details":"Minun, L83, F","condition":"235/235","active":false,"stats":{"atk":71,"def":131,"spa":172,"spd":189,"spe":205},"moves":["batonpass","encore","thunderbolt","substitute"],"baseAbility":"voltabsorb","item":"leftovers","pokeball":"pokeball","ability":"voltabsorb"},{"ident":"p2: Vespiquen","details":"Vespiquen, L83, F","condition":"251/251","active":false,"stats":{"atk":180,"def":217,"spa":180,"spd":217,"spe":114},"moves":["infestation","substitute","attackorder","healorder"],"baseAbility":"pressure","item":"leftovers","pokeball":"pokeball","ability":"pressure"},{"ident":"p2: Cresselia","details":"Cresselia, L79, F","condition":"319/319","active":false,"stats":{"atk":115,"def":235,"spa":164,"spd":251,"spe":180},"moves":["psychic","calmmind","icebeam","moonlight"],"baseAbility":"levitate","item":"leftovers","pokeball":"pokeball","ability":"levitate"},{"ident":"p2: Lucario","details":"Lucario, L73, F","condition":"223/223","active":false,"stats":{"atk":165,"def":145,"spa":210,"spd":145,"spe":174},"moves":["aurasphere","nastyplot","darkpulse","flashcannon"],"baseAbility":"innerfocus","item":"lucarionite","pokeball":"pokeball","ability":"innerfocus"},{"ident":"p2: Heliolisk","details":"Heliolisk, L79, F","condition":"228/228","active":false,"stats":{"atk":91,"def":128,"spa":218,"spd":194,"spe":218},"moves":["surf","hypervoice","hiddenpowerice60","thunderbolt"],"baseAbility":"dryskin","item":"choicespecs","pokeball":"pokeball","ability":"dryskin"}]},"rqid":9}

>battle-gen7randombattle-636352623↵↵|choice||move sludgewave↵|↵|switch|p1a: Whiscash|Whiscash, L83, F|100/100↵|move|p2a: Salazzle|Sludge Wave|p1a: Whiscash↵|-resisted|p1a: Whiscash↵|-crit|p1a: Whiscash↵|-damage|p1a: Whiscash|75/100↵|↵|upkeep↵|turn|4

>battle-gen7randombattle-636352623↵|inactive|Time left: 150 sec this turn | 190 sec total

1. client side behaviours
    - connecting to showdown server
    - logging in to showdown account
    - requesting matches from other players
    - fetching game state, i.e did other player move, parsing moves,
    - manging opponent timeout, quits
    - sending responses to showdown server
    - accepting match requests from players
    - supports many concurrent matches at once to learn from
    - cannot be single threaded networking code

2. black box model implementation with
   standardized pokemon interface for model inputs, cannot be single threaded code
   -- computing reward
   -- selecting action
   -- scoring current state
   -- training iteration loop
   -- saving model parameter weights



# Useful libs

import json
import lxml
import argparse
from threading import Thread, Lock
import os.path
import uuid
from tornado.concurrent import Future
import tornado.web

import tornado.ioloop
import tornado.escape
import tornado.options # used to dine options
tornado.websocket

import pygogo
import psutil


# organization of classes

Pokemon class -- holds pokemon type, stats, boosts, moves etc
Player class -- holds information of battling players in show down
Battle class -- the rooms being battled are being held in
ShowdownClient class -- the websocket connection to Showdown,
                     -- handling multiple concurrent battles, sending battle events to 
                     -- agents, signalling turns to agents etc.
Experience class -- holds a record of battles played
Agent class -- holds the RL agent for pokemon showdown, one of these agents is Human input

WebInterface class -- allows user to inspect agent model during battle, everytime we perform an update to a variable, publish it to server

Before the agent can run it also needs to be trained, which means iterating through many battles
this would require initiating many battles one by one till agent converges which means