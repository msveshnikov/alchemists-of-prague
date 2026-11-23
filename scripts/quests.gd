extends Node
## Quests (autoload "Quests"): named NPCs, the 20 quests of the game, their state, dialogue topics and world hooks.
##
## A quest is a list of stages; the current stage is the objective shown on the HUD, the compass, the map and in the
## journal. Stage kinds ("do"):
##   talk     — choose the stage's topic in a conversation with `npc`            (say: lines, give/take: items)
##   deliver  — like talk, but the topic only appears while you carry `items`   (they are taken)
##   kill     — kill `n` enemies: `kind` in `district`, or the stage's own `spawn` (outdoors, or inside `house`);
##              `drop` = items given when the stage is done, `bonus_fall` = reward if the target was thrown to death
##   pickup   — pick up the glowing `item` lying at `pos`
##   defenestrate — throw `n` enemies to their death (windows, bridge, walls) after accepting the quest
## Dialogue lines starting with "V:" are Václav's, "*" are narration, everything else is the NPC speaking.

signal changed

const XP_KILL := {"skeleton": 10, "alchemist": 15, "golem": 50}

## Named people. `replaces` = population id whose place, route, role and stall they take (so traders keep trading);
## otherwise `pos` + `yaw`. `portrait` defaults to the character model's portrait if there is one.
const NPCS := {
	"borek": {"name": "Sergeant Bořek", "character": "guard", "replaces": "guard#00", "schedule": "always",
		"greet": "Václav of Vyšehrad! The captain wrote you'd come. Good — the square needs every blade.",
		"who": ["Bořek, sergeant of the Old Town watch. Twenty years on this square and I've never seen nights like these."],
		"topics": [
			["Where can I get a better weapon?", ["Radim sells blades at the weapons stall on the east side of the square, by the smithy.",
				"A longer sword keeps the dead at arm's length. An axe cracks clay. Havel the smith will hone whatever you carry."]],
			["How do I survive the night?", ["Healing draughts from Jakub the barber — the potion stall in the middle of the market.",
				"Block with your shield (right mouse), roll away (Q). And when one of them reels — grab it and throw it out of a window.",
				"This is Prague. We have a tradition."]],
			["What if I get into trouble with the guard?", ["Don't steal in daylight and don't hurt honest folk. My men have long memories — but short ones too, give them a few minutes."]],
		]},
	"lazar": {"name": "Lazar the Beggar", "character": "beggar", "replaces": "beggar#03", "schedule": "always",
		"greet": "Alms, sir knight? Or are you here for something Lazar knows?",
		"who": ["Lazar. Once a cooper, now a beggar. The Týn church gives me shade, and the square gives me stories."],
		"topics": [["Any rumours?", ["They say the dead don't walk on the bridge — the river frightens them. They say a lot of things.",
			"Brother Anselm on the bridge reads any writing ever made. Even the devil's."]]]},
	"anselm": {"name": "Brother Anselm", "character": "monk", "replaces": "monk#01", "schedule": "always",
		"greet": "Pax tecum, my son. Have you come to pray, or to ask?",
		"who": ["Anselm, a poor brother of the Order of the Cross with the Red Star. I copied books for the archbishop once.",
			"Now I preach to the river. It listens better than most."]},
	"marketa": {"name": "Markéta, Innkeeper", "character": "market_woman", "replaces": "market_woman#27", "schedule": "always",
		"greet": "Welcome to the Golden Tankard! Beer, stew, a bed — pick one, or all three.",
		"who": ["Markéta. My father ran the Tankard and his father before him. The beds are lumpy, the beer is not."]},
	"jan": {"name": "Captain Jan", "character": "knight", "replaces": "knight#08", "schedule": "always",
		"greet": "Václav. Stand straight — the men are watching.",
		"who": ["Jan of Vyšehrad, captain of the garrison. I trained you, boy, or have you forgotten?"],
		"topics": [["Where can I buy heavier arms?", ["Our armourer at the stall by the gate sells greatswords. Expensive — but a greatsword reaches where an enemy thinks he is safe."]]]},
	"prokop": {"name": "Brother Prokop", "character": "monk", "replaces": "monk#08", "schedule": "always",
		"greet": "Peace be with you, knight. The dead are restless today.",
		"who": ["Prokop. I keep the graves by the rotunda of Saint Martin. Lately they keep me."]},
	"ota": {"name": "Sir Ota", "character": "knight", "replaces": "knight#07", "schedule": "day",
		"greet": "Another knight! Good, these puppies need someone to bite.",
		"who": ["Ota of Kutná Hora. Master-at-arms of Vyšehrad. Victor of eleven tourneys, loser of one — and that one was rigged."]},
	"bohuslav": {"name": "Gatekeeper Bohuslav", "character": "knight", "replaces": "knight#09", "schedule": "always",
		"greet": "Halt — ah, it's you, Václav. Pass.",
		"who": ["Bohuslav. I keep the gate of Vyšehrad, and the keys of the armoury. Mostly."]},
	"zbynek": {"name": "Old Zbyněk", "character": "merchant", "replaces": "merchant#24", "schedule": "always",
		"greet": "Hic! A knight! Sit, sit — Markéta, another one for the hero!",
		"who": ["Zbyněk. I was a councillor's clerk once. Now I'm the Tankard's most loyal guest."]},
	"anicka": {"name": "Anička", "character": "child_girl", "replaces": "child_girl#03", "schedule": "day",
		"greet": "Are you a real knight? With a real sword?",
		"who": ["I'm Anička! I live here with my uncle. Well, I did."]},
	"kunz": {"name": "Master Kunz", "character": "merchant", "replaces": "merchant#09", "schedule": "day",
		"greet": "Good day, sir knight. Cloth from Flanders and Florence — but not today, alas.",
		"who": ["Kunz, merchant of fine cloth. Half the burghers of Prague wear my wool, the other half owe me for it."]},
	"jakub": {"name": "Jakub the Barber", "character": "merchant", "replaces": "merchant#01", "schedule": "day",
		"greet": "Bleeding, pulling teeth, draughts for every ailment! What ails you, sir?",
		"who": ["Jakub, barber-surgeon of the Old Town. I sell healing draughts, vigour tonics and antidotes — the alchemists' poison is green, by the way."]},
	"dorota": {"name": "Dorota", "character": "market_woman", "replaces": "market_woman#07", "schedule": "day",
		"greet": "God keep you, sir knight. Fine day for the market, if the dead let us be.",
		"who": ["Dorota. I bake for half the square and gossip for the other half."]},
	"matej": {"name": "Watchman Matěj", "character": "guard", "replaces": "guard#02", "schedule": "always",
		"greet": "Sir knight. Quiet day. Too quiet for my stomach.",
		"who": ["Matěj of the Old Town watch. I guard the east side of the square — the smithy, the weapons stall."]},
	"kuba": {"name": "Little Kuba", "character": "child_boy", "replaces": "child_boy#00", "schedule": "day",
		"greet": "*sniff*... Hello.",
		"who": ["I'm Kuba. My papa is a cooper."]},
	"betka": {"name": "Bětka, Bread Woman", "character": "market_woman", "replaces": "market_woman#16", "schedule": "day",
		"greet": "Bread for the road, knight? The bridge is long and the river wind makes you hungry.",
		"who": ["Bětka. I sell bread at the bridge market and keep an eye on half the parcels in Prague."]},
	"vit": {"name": "Vít the Boatman", "character": "boatman", "pos": [-172.0, 0.0, 40.0], "yaw": 90.0, "schedule": "day",
		"greet": "Mind the steps, knight. The river bank is slippery as a priest's promise.",
		"who": ["Vít. I've poled barges up and down the Vltava for thirty years."]},
	"hynek": {"name": "Hynek, Castle Sentry", "character": "guard", "replaces": "guard#12", "schedule": "always",
		"greet": "Halt. The castle is closed to anyone without a summons.",
		"who": ["Hynek of the castle guard. I stand here so the King can sleep."]},
	"radim": {"name": "Radim the Armourer", "character": "merchant", "replaces": "merchant#04", "schedule": "day",
		"greet": "Steel, sir knight! Swords, axes, helmets and mail — the best of Prague, the cheapest of Bohemia.",
		"who": ["Radim, armourer. I don't forge, I sell — Havel next door forges and hones."],
		"topics": [["Which weapon should I buy?", ["The Bastard Sword: longer than your knightly blade — you hit them before they hit you.",
			"The War Axe: short, slower, but it splits golem clay like firewood.",
			"The Executioner's Greatsword is sold only at Vyšehrad: enormous reach, slow and heavy."]]]},
	"havel": {"name": "Havel the Smith", "character": "butcher", "replaces": "butcher#03", "schedule": "day",
		"greet": "*clang* ... What? Speak up, the anvil's louder than you.",
		"who": ["Havel, smith of the Old Town. Bring me any blade and coin, and I'll put an edge on it that splits a hair."]},
}

## The quests. `giver` offers it (the "!" over his head) once every quest in `requires` is done; `auto` quests start by
## themselves as soon as they are unlocked. `give` on the quest = items handed over when you accept.
const QUESTS := {
	# ======================================================================== main story
	"m1_night": {"title": "Night Watch", "main": true, "auto": true, "giver": "borek",
		"summary": "The dead walk on Old Town Square at night. Sergeant Bořek of the town watch needs every blade.",
		"stages": [
			{"do": "talk", "npc": "borek", "text": "Report to Sergeant Bořek by the Town Hall on Old Town Square.",
				"topic": "Sergeant, Václav of Vyšehrad reporting.",
				"say": ["Every night the dead climb out of the cellars around the square. Skeletons, mostly — bones held together by alchemy.",
					"My men won't go out after dark. You will. Break three of them on the square tonight and come back to me.",
					"V: And until nightfall?",
					"Look around the market: traders by day, Havel the smith at his forge, Jakub the barber with his draughts.",
					"If you're impatient, press T and wait for the dark."]},
			{"do": "kill", "kind": "skeleton", "n": 3, "district": "old_town", "at": [0.0, 0.0, 0.0],
				"text": "Destroy 3 skeletons on Old Town Square. They rise at night — press T to wait for dusk."},
			{"do": "talk", "npc": "borek", "text": "Return to Sergeant Bořek by the Town Hall.", "topic": "Three skeletons are dust.",
				"say": ["Ha! I heard the bones crack from the guardhouse. You'll do, Václav.",
					"The council pays for every night we survive. Take it."]},
		],
		"reward": {"gold": 40, "xp": 80, "items": {"potion_health": 1}}},
	"m2_bones": {"title": "Who Buys the Bones?", "main": true, "giver": "borek", "requires": ["m1_night"],
		"offer": "Is there more work, Sergeant?",
		"summary": "Someone in the Old Town buys bones from grave-robbers. Lazar the beggar may know who.",
		"intro": ["Plenty. Someone in the Old Town buys bones — grave-robbers carry sacks of them through the streets at dawn.",
			"Lazar the beggar sits by the Týn church, north of the square. He sees everything and says nothing — unless he's fed.",
			"Find out who the buyer is."],
		"stages": [
			{"do": "talk", "npc": "lazar", "text": "Ask Lazar the beggar by the Týn church (north of the square) who buys the bones.",
				"topic": "Lazar? Sergeant Bořek says you see everything.",
				"say": ["Lazar sees, Lazar starves. A loaf of bread clears the eyes wonderfully, sir knight.",
					"The bread women at the market sell it for three groschen."]},
			{"do": "deliver", "npc": "lazar", "items": {"bread": 1}, "text": "Bring Lazar a loaf of Rye Bread (bread stalls on the square).",
				"topic": "Here, a loaf of bread.",
				"say": ["God bless you! ... Mm. Now — the bone-buyer.",
					"His name is Jíra. He lives in the lane west of the Týn — first house on the left as you walk north from the square.",
					"Sacks go in at dawn. Screams come out at night. Be careful, knight."]},
			{"do": "kill", "n": 1, "house": "house_burgher_c#05", "spawn": [{"kind": "alchemist", "name": "Jíra the Bone-buyer", "hp": 1.4}],
				"drop": {"ledger": 1}, "text": "Deal with Jíra the bone-buyer in his house in the lane west of the Týn church."},
			{"do": "deliver", "npc": "borek", "items": {"ledger": 1}, "keep": true, "text": "Bring Jíra's ledger to Sergeant Bořek.",
				"topic": "Jíra is dead. He kept this ledger.",
				"say": ["Let me see... Numbers, signs, a black sun on every page. I can't read this devil's script.",
					"Keep it. I know who can."]},
		],
		"reward": {"gold": 60, "xp": 120}},
	"m3_cipher": {"title": "The Black Sun Cipher", "main": true, "giver": "borek", "requires": ["m2_bones"],
		"offer": "Who can read the ledger?",
		"summary": "Jíra's ledger is written in cipher. Brother Anselm on the Stone Bridge reads any script.",
		"intro": ["Brother Anselm. He preaches on the Stone Bridge, among the statues. Copied books for the archbishop before the drink got him.",
			"Take the ledger to him. Karlova street leads west from the square to the bridge tower."],
		"stages": [
			{"do": "deliver", "npc": "anselm", "items": {"ledger": 1}, "keep": true,
				"text": "Show the ledger to Brother Anselm on the Stone Bridge (west along Karlova street).",
				"topic": "Brother, can you read this ledger?",
				"say": ["Let me see. Hm. Hmm! Not Latin — a cipher. The cipher of the Brotherhood of the Black Sun.",
					"I can read it, but the ink hides half the words. Bring me two Mandrake Leaves; their juice makes hidden letters show.",
					"The herb women at the produce stalls sell them — there is one at the end of this bridge."]},
			{"do": "deliver", "npc": "anselm", "items": {"herb": 2}, "take": {"ledger": 1},
				"text": "Bring Brother Anselm 2 Mandrake Leaves (produce stalls on the square or at the bridge).",
				"topic": "Here are the mandrake leaves.",
				"say": ["Now watch... There. The Brotherhood of the Black Sun. Three cells, and a master over them.",
					"A clay giant guards their road over this very bridge. They brew in a laboratory in the Lesser Town. And they harvest the old graves of Vyšehrad.",
					"Above them all is one they call the Magister.",
					"Break the three cells, Václav, and the Magister will have to show himself. Ask me about each of them."]},
		],
		"reward": {"xp": 100}},
	"m4_golem": {"title": "The Clay Giant", "main": true, "giver": "anselm", "requires": ["m3_cipher"],
		"offer": "Tell me about the clay giant.",
		"summary": "A golem of the Black Sun guards the Stone Bridge.",
		"intro": ["It walks the bridge on the Old Town side, near the tower. Clay, twice the height of a man, letters burning on its brow.",
			"A sword hardly scratches it — an axe serves better. Bring me a shard of its clay, so I know it is broken."],
		"stages": [
			{"do": "kill", "n": 1, "spawn": [{"kind": "golem", "name": "The Bridge Golem", "pos": [-205.0, 0.0, 32.0], "yaw": 90.0}],
				"text": "Destroy the clay golem on the Stone Bridge, near the Old Town bridge tower."},
			{"do": "deliver", "npc": "anselm", "items": {"clay_shard": 1}, "text": "Bring a Golem Clay Shard to Brother Anselm.",
				"topic": "The golem is broken. Here is a shard.",
				"say": ["The letters are dead. Praise be. Keep your strength, Václav — take these."]},
		],
		"reward": {"gold": 80, "xp": 180, "items": {"potion_health": 2}}},
	"m5_lab": {"title": "The Laboratory", "main": true, "giver": "anselm", "requires": ["m3_cipher"],
		"offer": "Where is the laboratory?",
		"summary": "The Black Sun brews its poisons somewhere in Malá Strana, the Lesser Town across the river.",
		"intro": ["Somewhere in the Lesser Town, across this bridge. Ask Markéta, the innkeeper of the Golden Tankard —",
			"every rumour in Malá Strana passes over her counter."],
		"stages": [
			{"do": "talk", "npc": "marketa", "text": "Ask Markéta, innkeeper of the Golden Tankard in Malá Strana, about the alchemists.",
				"topic": "Markéta, have you seen alchemists around here?",
				"say": ["Alchemists? Hush! ... Two men in black rented the house right next to my tavern. They pay in silver and never eat.",
					"The windows glow green at night and the cats have all gone. Go and see — the next door along, on the right as you face my tavern."]},
			{"do": "kill", "n": 2, "house": "house_burgher_c#22",
				"spawn": [{"kind": "alchemist", "name": "Brewer of the Black Sun"}, {"kind": "alchemist", "name": "Brewer of the Black Sun"}],
				"drop": {"sun_seal": 1}, "text": "Clear the alchemists' laboratory in the house next to the Golden Tankard."},
			{"do": "deliver", "npc": "anselm", "items": {"sun_seal": 1}, "text": "Bring the Seal of the Black Sun to Brother Anselm.",
				"topic": "I found this seal in the laboratory.",
				"say": ["The Black Sun... and the Magister's own mark on the back. The second cell is broken. Well done, my son."]},
		],
		"reward": {"gold": 80, "xp": 180}},
	"m6_graves": {"title": "The Restless Graves", "main": true, "giver": "anselm", "requires": ["m3_cipher"],
		"offer": "And the graves of Vyšehrad?",
		"summary": "The Black Sun raises the dead of the old Vyšehrad cemetery.",
		"intro": ["Go to Captain Jan at Vyšehrad. South from the square along Melantrichova, then up the road between the walls.",
			"His garrison guards the old cemetery by the rotunda."],
		"stages": [
			{"do": "talk", "npc": "jan", "text": "Speak to Captain Jan at the Vyšehrad tiltyard (south of the Old Town, up the road between the walls).",
				"topic": "Captain, Brother Anselm sent me about the graves.",
				"say": ["So the monk believes it too. Every grave by the rotunda has been dug open — from inside.",
					"Five of the dead are walking the cemetery right now, in broad daylight. My knights are trained for war, not for corpses.",
					"Put them back in the ground."]},
			{"do": "kill", "n": 5, "spawn": [
					{"kind": "skeleton", "pos": [-122.0, 10.0, 138.0]}, {"kind": "skeleton", "pos": [-122.0, 10.0, 148.0]},
					{"kind": "skeleton", "pos": [-133.0, 10.0, 146.0]}, {"kind": "skeleton", "pos": [-124.0, 10.0, 130.0]},
					{"kind": "skeleton", "pos": [-136.0, 10.0, 150.0]}],
				"text": "Destroy the 5 skeletons in the Vyšehrad cemetery by the rotunda."},
			{"do": "talk", "npc": "jan", "text": "Report to Captain Jan.", "topic": "The cemetery is quiet again.",
				"say": ["I watched from the wall. That's how a knight of Vyšehrad fights.", "Take this mail — you'll need it against the Magister."]},
		],
		"reward": {"gold": 100, "xp": 180, "items": {"chainmail": 1}}},
	"m7_magister": {"title": "The Magister", "main": true, "giver": "anselm", "requires": ["m4_golem", "m5_lab", "m6_graves"],
		"offer": "The three cells are broken. What now?",
		"summary": "With his cells broken, the Magister of the Black Sun has nowhere left to hide.",
		"intro": ["Now the Magister must come out. I deciphered the last page: he lives in the Old Town,",
			"in the house by the gate of the Jewish Town, at the north-west corner beyond the square.",
			"His name is Ozzo. He was a court physician once. Now he is something else.",
			"He will have his creatures with him. And Václav — this is Prague. If you find yourself near a window..."],
		"stages": [
			{"do": "kill", "n": 1, "house": "house_burgher_f#17",
				"spawn": [{"kind": "alchemist", "name": "Magister Ozzo", "hp": 4.5, "dmg": 1.6, "scale": 1.15},
					{"kind": "skeleton", "name": "Ozzo's Servant", "target": false}],
				"bonus_fall": {"gold": 100, "xp": 100, "say": "The Magister leaves his house through the window — the most Prague of deaths!"},
				"text": "Kill Magister Ozzo in his house by the gate of the Jewish Town (north-west of the square)."},
			{"do": "talk", "npc": "borek", "text": "Tell Sergeant Bořek that the Magister is dead.", "topic": "Magister Ozzo is dead.",
				"say": ["Dead? The Magister himself? ... Then tonight Prague sleeps.",
					"Captain Jan must hear it from your own mouth. Go to Vyšehrad — I think he has something for you."]},
		],
		"reward": {"gold": 150, "xp": 300}},
	"m8_blade": {"title": "The Blade of Vyšehrad", "main": true, "auto": true, "giver": "jan", "requires": ["m7_magister"],
		"summary": "Captain Jan wants to see the man who killed the Magister.",
		"stages": [
			{"do": "talk", "npc": "jan", "text": "Report to Captain Jan at Vyšehrad.", "topic": "Captain, the Magister of the Black Sun is dead.",
				"say": ["I heard. All Prague heard — they say he left through his own window.",
					"Kneel, Václav. ... Rise, knight-commander of Vyšehrad.",
					"This blade was forged for the first lord of Vyšehrad. It has waited a long time for a hand worth its weight.",
					"* The main story is complete. The night still holds stragglers — and Prague still needs its knight."]},
		],
		"reward": {"gold": 300, "xp": 500, "items": {"w_vysehrad": 1}}},
	# ======================================================================== side quests
	"s_pork": {"title": "A Hungry Watchman", "giver": "matej",
		"offer": "You look troubled, watchman.",
		"summary": "Watchman Matěj can't leave his post and hasn't eaten since dawn.",
		"intro": ["Troubled? Starving! I've stood on this post since matins and the sergeant won't let me leave it.",
			"The cook at the spit roast on the west side sells roast pork — six groschen a piece. Bring me two and I'll pay you back with interest."],
		"stages": [
			{"do": "deliver", "npc": "matej", "items": {"meat": 2},
				"text": "Bring Watchman Matěj 2 pieces of Roast Pork (the cook at the spit roast, west side of the square).",
				"topic": "Two pieces of roast pork, as ordered.",
				"say": ["Saint Wenceslas bless you! Here. And a tip: get yourself a longer sword from Radim. The dead hate reach."]},
		],
		"reward": {"gold": 25, "xp": 40}},
	"s_toy": {"title": "The Wooden Horse", "giver": "kuba",
		"offer": "Why are you crying, boy?",
		"summary": "Little Kuba lost his wooden horse, Hrom, near the Town Hall.",
		"intro": ["I lost my horse! My wooden horse, Hrom! I was playing by the Town Hall and a bone-man chased me and I dropped him!",
			"It was by the Town Hall, on the side where the street goes west to the bridge."],
		"stages": [
			{"do": "pickup", "item": "toy_horse", "pos": [-34.0, 0.0, -14.0], "text": "Find Kuba's wooden horse by the Town Hall (west side of the square)."},
			{"do": "deliver", "npc": "kuba", "items": {"toy_horse": 1}, "text": "Return the wooden horse to little Kuba.", "topic": "Is this your horse?",
				"say": ["HROM! You found him! ... Here, sir knight, my lucky groschen. Mama says I shouldn't give it away, but you're a knight."]},
		],
		"reward": {"gold": 10, "xp": 40}},
	"s_cloth": {"title": "Cloth for Master Kunz", "giver": "kunz",
		"offer": "You seem worried, merchant.",
		"summary": "Master Kunz's bale of Flemish cloth is waiting for him at the Stone Bridge market.",
		"intro": ["Worried? I need my cloth! A bale of Flemish green, the best in Prague, paid in advance.",
			"The barge brought it to the Stone Bridge and Bětka, the bread woman at the bridge market, kept it for me. But I can't leave my customers.",
			"Fetch it and I'll pay you well."],
		"stages": [
			{"do": "talk", "npc": "betka", "give": {"cloth_bale": 1},
				"text": "Collect Master Kunz's bale of cloth from Bětka, the bread woman at the Stone Bridge market (end of Karlova street).",
				"topic": "I've come for Master Kunz's cloth.",
				"say": ["Finally! It's been taking up half my stall. Here — careful, it's heavy, and Kunz counts every thread."]},
			{"do": "deliver", "npc": "kunz", "items": {"cloth_bale": 1}, "text": "Bring the bale of cloth to Master Kunz on Old Town Square.",
				"topic": "Your bale of Flemish cloth.", "say": ["Not a thread missing! You'd make an honest merchant, sir knight. Fifty groschen, as promised."]},
		],
		"reward": {"gold": 50, "xp": 60}},
	"s_herbs": {"title": "The Barber's Herbs", "giver": "jakub",
		"offer": "Do you need anything, master barber?",
		"summary": "Jakub the barber needs ingredients for his healing draughts.",
		"intro": ["Always! My draughts need mandrake and toadstool, and the herb women raise their prices every week.",
			"Bring me three Mandrake Leaves and two Toadstools. I'll pay in healing draughts — worth more than coin at night."],
		"stages": [
			{"do": "deliver", "npc": "jakub", "items": {"herb": 3, "mushroom": 2},
				"text": "Bring Jakub 3 Mandrake Leaves and 2 Toadstools (produce stalls, or the pockets of alchemists).",
				"topic": "Here are your herbs.", "say": ["Fresh enough. Take these draughts — and don't drink them all at once."]},
		],
		"reward": {"xp": 60, "items": {"potion_health": 3}}},
	"s_bones": {"title": "Rest for the Dead", "giver": "prokop",
		"offer": "What troubles you, Brother?",
		"summary": "Brother Prokop wants to bury the bones of the fallen dead in consecrated ground.",
		"intro": ["The dead, my son. When the alchemists' skeletons fall, their bones are scattered like chaff.",
			"Bring me five handfuls of bone dust from the fallen. I will bury them in consecrated ground, so they never rise again.",
			"God will reward you. And so will I — with a blessing."],
		"stages": [
			{"do": "deliver", "npc": "prokop", "items": {"bone_dust": 5}, "text": "Bring Brother Prokop 5 Bone Dust (dropped by destroyed skeletons).",
				"topic": "I've brought the bone dust.",
				"say": ["Requiescant in pace. ... Kneel, Václav. Benedicat te omnipotens Deus.",
					"* Warmth spreads through your chest. Your maximum health increases."]},
		],
		"reward": {"xp": 80, "max_hp": 15}},
	"s_beer": {"title": "A Cask for the Tankard", "giver": "vit",
		"offer": "Waiting for someone, boatman?",
		"summary": "Vít the boatman needs a cask of Pilsen beer carried to the Golden Tankard in Malá Strana.",
		"intro": ["Waiting for a fool to carry this cask, aye. Pilsen beer for the Golden Tankard in Malá Strana.",
			"The bridge is no place for a boatman with a cask and a bad back. Take it to Markéta, the innkeeper. She'll pay you."],
		"give": {"cask": 1},
		"stages": [
			{"do": "deliver", "npc": "marketa", "items": {"cask": 1},
				"text": "Deliver the cask of beer to Markéta at the Golden Tankard in Malá Strana (across the Stone Bridge).",
				"topic": "A cask of Pilsen beer from Vít the boatman.",
				"say": ["At last! The regulars were about to drink the river. Here's your coin, knight."]},
		],
		"reward": {"gold": 40, "xp": 60}},
	"s_duel": {"title": "A Lesson in Steel", "giver": "ota",
		"offer": "Are you training these men, sir?",
		"summary": "Sir Ota wants his squire taught some humility.",
		"intro": ["Training? Whipping puppies. Lev, my squire, thinks he's the best sword in Vyšehrad.",
			"Show him otherwise. Fight him here at the tiltyard — until he yields, not to the death!"],
		"stages": [
			{"do": "kill", "n": 1, "spawn": [{"kind": "knight", "name": "Squire Lev", "pos": [-170.0, 10.0, 176.0], "duel": true}],
				"text": "Defeat Squire Lev in a duel at the Vyšehrad tiltyard — until he yields."},
			{"do": "talk", "npc": "ota", "text": "Return to Sir Ota.", "topic": "Your squire has yielded.",
				"say": ["Ha! He'll be humble for a week. Take these gauntlets — I won them in a tourney at Kutná Hora."]},
		],
		"reward": {"gold": 30, "xp": 90, "items": {"gloves": 1}}},
	"s_key": {"title": "The Armoury Key", "giver": "bohuslav",
		"offer": "Is something wrong, gatekeeper?",
		"summary": "One of the dead stole the key of the Vyšehrad armoury from Gatekeeper Bohuslav.",
		"intro": ["Wrong? I've lost the armoury key, that's what. One of the dead from the graveyard grabbed it off my belt last night!",
			"Old Ondřej, the sexton that was. He wanders among the graves just inside the gate. Bring the key back before the captain notices."],
		"stages": [
			{"do": "kill", "n": 1, "spawn": [{"kind": "skeleton", "name": "Old Ondřej", "pos": [-84.0, 10.0, 142.0], "hp": 1.6}],
				"drop": {"armoury_key": 1}, "text": "Destroy Old Ondřej in the graveyard inside the Vyšehrad gate and take the key."},
			{"do": "deliver", "npc": "bohuslav", "items": {"armoury_key": 1}, "text": "Return the armoury key to Gatekeeper Bohuslav.",
				"topic": "Your key. Old Ondřej won't need it.", "say": ["Bless you! Here — a helmet from the armoury. Nobody counts them anyway."]},
		],
		"reward": {"xp": 80, "items": {"helmet": 1}}},
	"s_letter": {"title": "A Letter for the Castle", "giver": "jan", "requires": ["m6_graves"],
		"offer": "Do you need a messenger, Captain?",
		"summary": "Captain Jan's letter must reach the castle above Malá Strana.",
		"intro": ["As it happens, yes. This letter must reach the castle — but the castle guard lets no one pass.",
			"Give it to Hynek, the sentry at the castle gate, at the top of the stairs in Malá Strana."],
		"give": {"letter": 1},
		"stages": [
			{"do": "deliver", "npc": "hynek", "items": {"letter": 1},
				"text": "Deliver Captain Jan's letter to Hynek, the sentry at the castle gate (top of the stairs in Malá Strana).",
				"topic": "A letter from Captain Jan of Vyšehrad.",
				"say": ["From the captain? Give it here. ... It'll be with the chamberlain by vespers. Here, for your boots."]},
		],
		"reward": {"gold": 50, "xp": 70}},
	"s_defen": {"title": "A Prague Tradition", "giver": "zbynek",
		"offer": "You look like a man with a story.",
		"summary": "Old Zbyněk in the Golden Tankard wants to see the oldest Prague tradition honoured.",
		"intro": ["Story? I've got THE story. In Prague, hic, we settle arguments through the window. Out! Splat! Argument settled.",
			"Throw three of the devil's creatures to their deaths — out of windows, off the bridge, off the walls — and my lucky ring is yours."],
		"stages": [
			{"do": "defenestrate", "n": 3, "text": "Throw 3 enemies to their deaths: out of windows, off the bridge into the Vltava, or off the Vyšehrad walls."},
			{"do": "talk", "npc": "zbynek", "text": "Tell old Zbyněk about your throws (the Golden Tankard, Malá Strana).",
				"topic": "Three of them went flying.", "say": ["Three! A true Praguer! Here's the ring — it kept me standing through forty years of beer."]},
		],
		"reward": {"xp": 100, "items": {"ring": 1}}},
	"s_basket": {"title": "Bread for the Brothers", "giver": "dorota",
		"offer": "Can I help you, good woman?",
		"summary": "Dorota the baker sends bread to Brother Anselm on the Stone Bridge.",
		"intro": ["Oh, a knight with manners! Brother Anselm preaches on the Stone Bridge and forgets to eat.",
			"Take him this basket of bread from me. Karlova street goes west from the square to the bridge tower."],
		"give": {"bread_basket": 1},
		"stages": [
			{"do": "deliver", "npc": "anselm", "items": {"bread_basket": 1}, "text": "Take Dorota's basket of bread to Brother Anselm on the Stone Bridge.",
				"topic": "Dorota from the market sends you bread.",
				"say": ["Dorota, that saint of a woman! Thank you, my son. Take a coin for your trouble.",
					"And come to me if you ever find writing you cannot read."]},
		],
		"reward": {"gold": 15, "xp": 40}},
	"s_haunted": {"title": "The Haunted House", "giver": "anicka",
		"offer": "What's the matter, little one?",
		"summary": "Skeletons have moved into the house of Anička's uncle in Malá Strana.",
		"intro": ["There are bone-men in my uncle's house! The stone one on the tavern's side of the street, just past the castle stairs.",
			"Uncle ran away to the castle. Please make them go away, sir knight!"],
		"stages": [
			{"do": "kill", "n": 2, "house": "house_burgher_c#23", "spawn": [{"kind": "skeleton"}, {"kind": "skeleton"}],
				"text": "Clear the skeletons from the house of Anička's uncle (stone house west of the castle stairs, Malá Strana)."},
			{"do": "talk", "npc": "anicka", "text": "Tell Anička her uncle's house is safe.", "topic": "The bone-men are gone.",
				"say": ["Really? You're the bravest knight in Prague! Uncle left this for whoever helps — here!"]},
		],
		"reward": {"gold": 30, "xp": 70, "items": {"potion_stamina": 1}}},
}

# ---------------------------------------------------------------- state
var state := {}            # quest id -> {"stage": int, "count": int, "done": bool}
var tracked := ""          # quest shown on the HUD tracker / compass
var world: Node = null
var npc_home := {}         # npc id -> Vector3 (where they stand / their route start)
var npc_schedule := {}     # npc id -> "day" / "always"
var npc_nodes := {}        # npc id -> spawned Npc
var _enemies := {}         # quest id -> Array[Enemy] spawned for the current kill stage
var _pickup := {}          # quest id -> pickup Node3D
var _tick := 0.0


func reset() -> void:
	state = {}
	tracked = ""
	_check_unlocks(true)
	changed.emit()


func to_save() -> Dictionary:
	return {"state": state.duplicate(true), "tracked": tracked}


func from_save(d: Dictionary) -> void:
	state = {}
	var s: Dictionary = d.get("state", {})
	for q in s:
		if QUESTS.has(q):
			state[q] = {"stage": int(s[q].get("stage", 0)), "count": int(s[q].get("count", 0)), "done": bool(s[q].get("done", false))}
	tracked = String(d.get("tracked", ""))
	_check_unlocks(true)
	if tracked == "" or not is_active(tracked):
		_pick_tracked()
	changed.emit()


# ---------------------------------------------------------------- queries
func is_active(q: String) -> bool:
	return state.has(q) and not state[q]["done"]


func is_done(q: String) -> bool:
	return state.has(q) and state[q]["done"]


func is_available(q: String) -> bool:
	if state.has(q):
		return false
	for r in QUESTS[q].get("requires", []):
		if not is_done(r):
			return false
	return true


func stage(q: String) -> Dictionary:
	if not is_active(q):
		return {}
	var st: Array = QUESTS[q]["stages"]
	return st[min(state[q]["stage"], st.size() - 1)]


func active_quests() -> Array:
	var out: Array = []
	for q in QUESTS:
		if is_active(q):
			out.append(q)
	out.sort_custom(func(a, b): return QUESTS[a].get("main", false) and not QUESTS[b].get("main", false))
	return out


func done_quests() -> Array:
	return QUESTS.keys().filter(func(q): return is_done(q))


## Quests someone is waiting to give you: [quest id, giver id], main story first.
func offered() -> Array:
	var out: Array = []
	for q in QUESTS:
		if is_available(q) and not QUESTS[q].get("auto", false):
			out.append([q, QUESTS[q]["giver"]])
	out.sort_custom(func(a, b): return QUESTS[a[0]].get("main", false) and not QUESTS[b[0]].get("main", false))
	return out


## Where someone can be found, in words: "Old Town Square" etc.
func npc_place(id: String) -> String:
	if _world_ok() and npc_home.has(id):
		return world.district_name(world.district_at(npc_home[id]))
	return ""


func npc_name(id: String) -> String:
	return NPCS[id]["name"] if NPCS.has(id) else id


func _stage_items(s: Dictionary) -> Dictionary:
	return s.get("items", {})


func _has_items(items: Dictionary) -> bool:
	for id in items:
		if Game.count(id) < int(items[id]):
			return false
	return true


## Objective line with progress, e.g. "Destroy 5 skeletons ... (2/5)".
func objective(q: String) -> String:
	var s := stage(q)
	if s.is_empty():
		return ""
	var t: String = s["text"]
	match s["do"]:
		"kill", "defenestrate":
			t += "  (%d/%d)" % [state[q]["count"], int(s.get("n", 1))]
		"deliver":
			var parts: Array = []
			var items := _stage_items(s)
			for id in items:
				parts.append("%d/%d" % [min(Game.count(id), int(items[id])), int(items[id])])
			t += "  (" + ", ".join(parts) + ")"
	if s.has("npc") and npc_schedule.get(s["npc"], "always") == "day" and _world_ok() and world.day_night and world.day_night.is_night:
		t += "  — by day"
	return t


## Where the objective is (for compass / map / tracker), or null.
func target(q: String) -> Variant:
	var s := stage(q)
	if s.is_empty():
		return null
	match s["do"]:
		"talk", "deliver":
			var id: String = s["npc"]
			var n = npc_nodes.get(id)
			if n != null and is_instance_valid(n) and not n.dead:
				return n.global_position
			return npc_home.get(id)
		"kill":
			if s.has("house") and _world_ok():
				var dm: Dictionary = world.marker("MARK_door@" + String(s["house"]))
				if not dm.is_empty():
					return world.v3(dm["pos"])
			var best = null
			for e in _enemies.get(q, []):
				if is_instance_valid(e) and not e.is_dead() and e.get_meta("quest_target", true):
					if best == null or (_world_ok() and e.global_position.distance_to(world.player.global_position) < best.distance_to(world.player.global_position)):
						best = e.global_position
			if best != null:
				return best
			if s.has("spawn") and s["spawn"][0].has("pos"):
				var p: Array = s["spawn"][min(state[q]["count"], s["spawn"].size() - 1)].get("pos", s["spawn"][0]["pos"])
				return Vector3(p[0], p[1], p[2])
			if s.has("at"):
				return Vector3(s["at"][0], s["at"][1], s["at"][2])
		"pickup":
			return Vector3(s["pos"][0], s["pos"][1], s["pos"][2])
	return null


## "!" = has a quest for you, "?" = you have something to tell / bring them, "…" = you still have to bring them
## something, "" = nothing.
func npc_marker(id: String) -> String:
	var bring := false
	for q in QUESTS:
		var s := stage(q)
		if not s.is_empty() and s.get("npc", "") == id:
			if s["do"] == "talk" or _has_items(_stage_items(s)):
				return "?"
			bring = true
	for q in QUESTS:
		if QUESTS[q]["giver"] == id and is_available(q) and not QUESTS[q].get("auto", false):
			return "!"
	return "…" if bring else ""


# ---------------------------------------------------------------- dialogue
## Topics for a conversation: [{text, lines, act (Callable or null), kind}]. kind: quest/new/info/trade/smith/inn/bye.
func topics(id: String) -> Array:
	var out: Array = []
	var d: Dictionary = NPCS.get(id, {})
	for q in QUESTS:
		var s := stage(q)
		if s.is_empty() or s.get("npc", "") != id:
			continue
		if s["do"] == "deliver" and not _has_items(_stage_items(s)):
			continue
		out.append({"text": s["topic"], "lines": s.get("say", []), "act": _finish_stage.bind(q), "kind": "quest"})
	for q in QUESTS:
		if QUESTS[q]["giver"] == id and is_available(q) and not QUESTS[q].get("auto", false):
			var qq: Dictionary = QUESTS[q]
			out.append({"text": qq["offer"], "lines": qq.get("intro", []), "act": start.bind(q), "kind": "new"})
	for q in QUESTS:   # reminders: what was I supposed to do for you?
		var s2 := stage(q)
		if not s2.is_empty() and QUESTS[q]["giver"] == id and s2.get("npc", "") != id:
			out.append({"text": "About \"%s\"..." % QUESTS[q]["title"], "lines": QUESTS[q].get("intro", []) + ["* " + objective(q)], "act": null, "kind": "info"})
	out.append({"text": "Who are you?", "lines": d.get("who", ["..."]), "act": null, "kind": "info"})
	for t in d.get("topics", []):
		out.append({"text": t[0], "lines": t[1], "act": null, "kind": "info"})
	return out


func start(q: String) -> void:
	if state.has(q):
		return
	state[q] = {"stage": 0, "count": 0, "done": false}
	var qq: Dictionary = QUESTS[q]
	for id in qq.get("give", {}):
		Game.add_item(id, int(qq["give"][id]))
	Game.journal.append("New quest: %s%s %s" % [qq["title"], "" if qq["title"].ends_with("?") else ".", qq["summary"]])
	_announce("New quest: " + qq["title"], objective(q))
	if tracked == "" or qq.get("main", false) or not is_active(tracked):
		tracked = q
	Sfx.play("paper")
	_enter_stage(q)
	changed.emit()


func _finish_stage(q: String) -> void:
	var s := stage(q)
	if s.is_empty():
		return
	if s["do"] == "deliver" and not s.get("keep", false):
		var items := _stage_items(s)
		for id in items:
			Game.add_item(id, -int(items[id]), true)
		Game.say("Handed over: " + ", ".join(items.keys().map(func(i): return Game.ITEMS[i]["name"])), Color(0.85, 0.8, 0.65))
	for id in s.get("take", {}):
		Game.add_item(id, -int(s["take"][id]), true)
	for id in s.get("give", {}):
		Game.add_item(id, int(s["give"][id]))
	advance(q)


func advance(q: String) -> void:
	if not is_active(q):
		return
	var s := stage(q)
	for id in s.get("drop", {}):
		Game.add_item(id, int(s["drop"][id]))
	_clear_world(q)
	state[q]["stage"] += 1
	state[q]["count"] = 0
	if state[q]["stage"] >= QUESTS[q]["stages"].size():
		_complete(q)
	else:
		Sfx.play("paper")
		_announce(QUESTS[q]["title"], objective(q))
		_enter_stage(q)
	changed.emit()


func _complete(q: String) -> void:
	state[q]["done"] = true
	var qq: Dictionary = QUESTS[q]
	var r: Dictionary = qq.get("reward", {})
	if r.has("gold"):
		Game.add_gold(int(r["gold"]))
		Sfx.play("coin")
	for id in r.get("items", {}):
		Game.add_item(id, int(r["items"][id]))
	if r.has("max_hp"):
		Game.max_hp += float(r["max_hp"])
		Game.hp = Game.max_hp
		Game.say("Maximum health +%d" % int(r["max_hp"]), Color(1, 0.6, 0.5))
		Game.stats_changed.emit()
	Game.journal.append("Quest complete: %s" % qq["title"] + ("" if qq["title"].ends_with("?") else "."))
	_announce("Quest complete: " + qq["title"], "")
	if r.has("xp"):
		Game.add_xp(int(r["xp"]))
	if tracked == q:
		_pick_tracked()
	_check_unlocks(false, q)


## Start "auto" quests whose requirements are met; announce the givers of quests that `just_done` unlocked.
func _check_unlocks(quiet: bool, just_done := "") -> void:
	for q in QUESTS:
		var qq: Dictionary = QUESTS[q]
		if not is_available(q) or (qq.get("requires", []).is_empty() and not qq.get("auto", false)):
			continue
		if qq.get("auto", false):
			if quiet:
				state[q] = {"stage": 0, "count": 0, "done": false}
				if tracked == "":
					tracked = q
			else:
				start(q)
		elif not quiet and just_done in qq.get("requires", []):
			Game.say("%s has a new task for you: \"%s\"" % [npc_name(qq["giver"]), qq["title"]], Color(1.0, 0.85, 0.4))


func _pick_tracked() -> void:
	tracked = ""
	var act := active_quests()
	if not act.is_empty():
		tracked = act[0]


func set_tracked(q: String) -> void:
	if is_active(q):
		tracked = q
		changed.emit()


func _world_ok() -> bool:
	return world != null and is_instance_valid(world) and world.is_inside_tree()


func _announce(title: String, text: String) -> void:
	if _world_ok() and world.hud and world.hud.has_method("quest_banner"):
		world.hud.quest_banner(title, text)
	else:
		Game.say(title, Color(1.0, 0.85, 0.4))


# ---------------------------------------------------------------- world hooks
## Called by the world after it loaded its population: put the named people in place of ordinary townsfolk.
func patch_population(p_world: Node, population: Array) -> void:
	world = p_world
	npc_nodes = {}
	_enemies = {}
	_pickup = {}
	var by_id := {}
	for e in population:
		by_id[e["id"]] = e
	for id in NPCS:
		var d: Dictionary = NPCS[id]
		var e: Dictionary
		if d.has("replaces") and by_id.has(d["replaces"]):
			e = by_id[d["replaces"]]
		else:
			var p: Array = d.get("pos", [0.0, 0.0, 0.0])
			e = {"id": "q_" + id, "pos": p, "yaw_deg": float(d.get("yaw", 0.0)), "animation": "idle", "role": "named"}
			population.append(e)
		e["character"] = d["character"]
		e["quest_npc"] = id
		e["schedule"] = d.get("schedule", "always")
		if e.get("animation", "idle") in ["spar", "work", "pray", "beg", "cast"] and d["character"] in ["knight", "guard"]:
			e["animation"] = "idle"
		npc_home[id] = Vector3(e["pos"][0], e["pos"][1], e["pos"][2])
		npc_schedule[id] = e["schedule"]


func register_npc(id: String, n: Node) -> void:
	npc_nodes[id] = n


## Every frame from world._process: spawn quest enemies / pickups near the player.
func tick(delta: float) -> void:
	if not _world_ok() or world.player == null:
		return
	_tick -= delta
	if _tick > 0.0:
		return
	_tick = 1.0
	var pp: Vector3 = world.player.global_position
	for q in active_quests():
		var s := stage(q)
		match s["do"]:
			"kill":
				if not s.has("spawn") or s.has("house") or world.inside_house:
					continue
				var alive: Array = _enemies.get(q, []).filter(func(e): return is_instance_valid(e) and not e.is_dead())
				var p0: Array = s["spawn"][0]["pos"]
				var d := pp.distance_to(Vector3(p0[0], p0[1], p0[2]))
				if alive.is_empty() and d < 110.0:
					_spawn_enemies(q, s, null)
				elif not alive.is_empty() and d > 170.0:
					_clear_world(q)
			"pickup":
				if not _pickup.has(q) or not is_instance_valid(_pickup[q]):
					_spawn_pickup(q, s)


## Called when the player enters a house: spawn the enemies of a quest that lives there.
func on_enter_house(hid: String, root: Node3D, frame: Dictionary) -> void:
	for q in active_quests():
		var s := stage(q)
		if s["do"] != "kill" or s.get("house", "") != hid:
			continue
		var alive: Array = _enemies.get(q, []).filter(func(e): return is_instance_valid(e) and not e.is_dead())
		if alive.is_empty():
			_spawn_enemies(q, s, {"root": root, "frame": frame})


func house_has_quest(hid: String) -> bool:
	for q in active_quests():
		if stage(q).get("house", "") == hid:
			return true
	return false


func _spawn_enemies(q: String, s: Dictionary, house) -> void:
	var list: Array = []
	var specs: Array = s["spawn"]
	var targets_left := int(s.get("n", 1)) - int(state[q]["count"])
	var k := 0
	for sp in specs:
		var is_target: bool = sp.get("target", true)
		if is_target:
			if targets_left <= 0:
				continue
			targets_left -= 1
		var en := Enemy.new()
		var pos: Vector3
		var yaw := deg_to_rad(float(sp.get("yaw", randf() * 360.0)))
		if house != null:
			var f: Dictionary = house["frame"]
			var node: Node3D = f["node"]
			var zb: float = f["depth"] / 2.0 - f["inset"] - 6.5
			var lp := Vector3(-1.4 + 1.4 * (k % 3), f["floor"] + 0.1, zb + 3.6 + 1.2 * int(k / 3))
			pos = node.to_global(lp)
			yaw = node.rotation.y + PI
		else:
			pos = Vector3(sp["pos"][0], sp["pos"][1] + 0.1, sp["pos"][2])
		en.setup(sp["kind"], world, pos, yaw, "cast" if sp["kind"] == "alchemist" else "idle")
		en.customize(sp)
		en.set_meta("quest", q)
		en.set_meta("quest_target", is_target)
		if house != null:
			en.interior = house["root"]
		world.add_child(en)
		world.enemies.append(en)
		list.append(en)
		k += 1
	_enemies[q] = list


func _spawn_pickup(q: String, s: Dictionary) -> void:
	var root := Node3D.new()
	root.name = "QuestPickup_" + q
	world.add_child(root)
	root.global_position = Vector3(s["pos"][0], s["pos"][1], s["pos"][2])
	var lbl := Label3D.new()
	lbl.text = "✦"
	lbl.font = Game.FONT_BODY
	lbl.font_size = 96
	lbl.modulate = Color(1.0, 0.85, 0.35)
	lbl.outline_size = 12
	lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lbl.position.y = 0.9
	root.add_child(lbl)
	var tw := lbl.create_tween().set_loops()
	tw.tween_property(lbl, "position:y", 1.2, 0.8).set_trans(Tween.TRANS_SINE)
	tw.tween_property(lbl, "position:y", 0.9, 0.8).set_trans(Tween.TRANS_SINE)
	var icon := Sprite3D.new()
	icon.texture = Game.icon(Game.ITEMS[s["item"]]["icon"])
	icon.pixel_size = 0.004
	icon.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	icon.position.y = 0.3
	root.add_child(icon)
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.8, 0.4)
	light.light_energy = 1.6
	light.omni_range = 3.5
	light.position.y = 0.8
	root.add_child(light)
	_pickup[q] = root
	var item: String = s["item"]
	world.interactables.append({"pos": root.global_position, "radius": 2.0, "kind": "pickup", "node": root,
		"label": "Pick up: " + Game.ITEMS[item]["name"],
		"action": func(): _on_pickup(q, item),
		"enabled": func(): return is_instance_valid(root) and not world.inside_house})


func _on_pickup(q: String, item: String) -> void:
	Sfx.play("cloth")
	Game.add_item(item, 1)
	advance(q)


func _clear_world(q: String) -> void:
	if _pickup.has(q):
		var n = _pickup[q]
		_pickup.erase(q)
		if is_instance_valid(n):
			if _world_ok():
				world.interactables = world.interactables.filter(func(it): return not it.has("node") or it["node"] != n)
			n.queue_free()
	if _enemies.has(q):
		for e in _enemies[q]:
			if is_instance_valid(e) and not e.is_dead() and _world_ok():
				world.enemies.erase(e)
				e.queue_free()
		_enemies.erase(q)


func on_kill(e: Node, by_fall: bool) -> void:
	var tag: String = e.get_meta("quest", "")
	for q in active_quests():
		var s := stage(q)
		var hit := false
		match s["do"]:
			"kill":
				if s.has("spawn"):
					hit = tag == q and e.get_meta("quest_target", true)
				else:
					hit = e.kind == s.get("kind", "") and (not s.has("district") or world.district_at(e.global_position) == s["district"])
			"defenestrate":
				hit = by_fall
		if not hit:
			continue
		state[q]["count"] += 1
		if by_fall and s.has("bonus_fall"):
			var b: Dictionary = s["bonus_fall"]
			Game.say(b.get("say", "Out of the window!"), Color(1.0, 0.75, 0.3))
			Game.add_gold(int(b.get("gold", 0)))
			Game.add_xp(int(b.get("xp", 0)))
		if state[q]["count"] >= int(s.get("n", 1)):
			if tag == q:
				_enemies.erase(q)      # the stage's last foe: leave the corpse where it fell
			advance(q)
		else:
			Game.say(objective(q), Color(0.95, 0.85, 0.55))
			changed.emit()


func _enter_stage(q: String) -> void:
	var s := stage(q)
	if s.is_empty():
		return
	if _world_ok() and s["do"] == "kill" and s.has("house") and world.inside_house and world.current_house == s["house"]:
		var it: Dictionary = world.interiors.get(s["house"], {})
		if not it.is_empty():
			on_enter_house(s["house"], it["root"], world._house_frame(s["house"]))


func _ready() -> void:
	reset()
