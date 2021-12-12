import smartpy as sp

class SoccerBetFactory(sp.Contract):
    def __init__(self, admin):
        self.init(
            admin = admin,
            games = sp.map(tkey = sp.TString)
        )
    
    @sp.entry_point
    def new_game(self, params):
        sp.verify_equal(sp.sender, self.data.admin, message = "Error: you cannot initialize a new game")
        sp.verify(~ self.data.games.contains(params.game_id))

        self.data.games[params.game_id] = sp.record(
            team_a = params.team_a,
            team_b = params.team_b,
            status = sp.int(0),
            outcome = sp.int(-1),
            total_bet_amount = sp.tez(0),
            bet_amount_on = sp.record(team_a = sp.tez(0),team_b = sp.tez(0), tie = sp.tez(0)),
            redeemed = sp.int(0),
            bets_by_choice = sp.record(team_a = sp.int(0), team_b = sp.int(0), tie = sp.int(0)),
            bet_amount_by_user = sp.map(
                tkey = sp.TAddress, 
                tvalue = sp.TRecord(team_a = sp.TMutez, team_b = sp.TMutez, tie = sp.TMutez)
            )
        )

    @sp.entry_point
    def add_bet(self, params):
        sp.verify((params.choice == 0) | (params.choice == 1) | (params.choice == 2), message = "Error: you must prompt a value comprised in {0;1;2}")
        sp.verify(self.data.games.contains(params.game_id))
        game = self.data.games[params.game_id]

        sp.verify_equal(game.status, 0, message = "Error: you cannot place a bet anymore")
        sp.verify(sp.amount >= sp.mutez(100000), message = "Error: your bet must be equal or higher than 0.1 XTZ")

        sp.if ~game.bet_amount_by_user.contains(sp.sender):
            game.bet_amount_by_user[sp.sender] = sp.record(
                team_a = sp.tez(0),
                team_b = sp.tez(0),
                tie    = sp.tez(0))

        sp.if params.choice == 0:
            game.bet_amount_by_user[sp.sender].team_a += sp.amount
            game.bet_amount_on.team_a += sp.amount
            game.bets_by_choice.team_a += sp.int(1)
        sp.if params.choice == 1:
            game.bet_amount_by_user[sp.sender].team_b += sp.amount
            game.bet_amount_on.team_b += sp.amount
            game.bets_by_choice.team_b += sp.int(1)

        sp.if params.choice == 2:
            game.bet_amount_by_user[sp.sender].tie += sp.amount
            game.bet_amount_on.tie += sp.amount
            game.bets_by_choice.tie += sp.int(1)

        game.total_bet_amount = game.bet_amount_on.team_a + game.bet_amount_on.team_b + game.bet_amount_on.tie 

    @sp.entry_point
    def remove_bet(self, params):
        sp.verify((params.choice == 0) | (params.choice == 1) | (params.choice == 2), message = "Error: you must prompt a value comprised in {0;1;2}")
        sp.verify(self.data.games.contains(params.game_id), message = "Error: this match does not exist")
        game = self.data.games[params.game_id]
        sp.verify_equal(game.status, 0, message = "Error: you cannot remove your bet anymore")
        sp.verify(game.bet_amount_by_user.contains(sp.sender), message = "Error: you do not have any bets to remove")
        amount_to_send = sp.local("amount_to_send", sp.tez(0))

        bet_by_user = game.bet_amount_by_user[sp.sender]
        fees = sp.mutez(0)
        sp.if params.choice == 0:
            sp.verify(bet_by_user.team_a > sp.tez(0), message = "Error: you have not placed any bets on this outcome")
            game.bet_amount_on.team_a -= bet_by_user.team_a
            amount_to_send.value = bet_by_user.team_a
            self.data.games[params.game_id].bets_by_choice.team_a -= sp.int(1)
            bet_by_user.team_a = sp.tez(0)

        sp.if params.choice == 1:
            sp.verify(bet_by_user.team_b > sp.tez(0), message = "Error: you have not placed any bets on this outcome")
            game.bet_amount_on.team_b -= bet_by_user.team_b  
            amount_to_send.value = bet_by_user.team_b
            self.data.games[params.game_id].bets_by_choice.team_b -= sp.int(1)       
            bet_by_user.team_b = sp.tez(0)

        sp.if params.choice == 2:
            sp.verify(bet_by_user.tie > sp.tez(0), message = "Error: you have not placed any bets on this outcome")
            game.bet_amount_on.tie -= bet_by_user.tie 
            amount_to_send.value = bet_by_user.tie
            self.data.games[params.game_id].bets_by_choice.tie -= sp.int(1)   
            bet_by_user.tie = sp.tez(0)   
        
        sp.send(sp.sender, amount_to_send.value - fees)
        game.total_bet_amount = game.bet_amount_on.team_a + game.bet_amount_on.team_b + game.bet_amount_on.tie 

        sp.if (bet_by_user.team_a == sp.mutez(0)) & (bet_by_user.team_b == sp.tez(0)) & (bet_by_user.tie == sp.tez(0)):
            del game.bet_amount_by_user[sp.sender]

    @sp.entry_point
    def next_status(self, params):
        sp.verify_equal(sp.sender, self.data.admin, message = "Error: you cannot update the game status")
        sp.verify(self.data.games.contains(params.game_id), message = "Error: this match does not exist")
        game = self.data.games[params.game_id]
        sp.if game.status == sp.int(1):
            game.status += 1
        sp.if game.status == sp.int(0):
            game.status += 1

    @sp.entry_point
    def set_outcome(self, params):
        sp.verify((params.choice == 0) | (params.choice == 1) | (params.choice == 2), message = "Error: you must prompt a value comprised in {0;1;2}")
        sp.verify_equal(sp.sender, self.data.admin, message = "Error: you cannot update the game status")
        sp.verify(self.data.games.contains(params.game_id), message = "Error: this match does not exist")
        game = self.data.games[params.game_id]
        sp.verify_equal(game.status, 1, "Error: the game outcome cannot be updated")
        game.outcome = params.choice

    @sp.entry_point
    def redeem_tez(self, params):
        sp.verify(self.data.games.contains(params.game_id), message = "Error: this match does not exist anymore!")
        game = self.data.games[params.game_id]
        sp.verify(game.bet_amount_by_user.contains(sp.sender), message = "Error: you did not place a bet on this match")
        sp.verify_equal(game.status, sp.int(2), "Error: you cannot redeem your gains before the match has ended")
        bet_by_user = game.bet_amount_by_user[sp.sender]
        sp.verify( ( ( game.outcome == sp.int(0) ) & ( bet_by_user.team_a > sp.tez(0) ) ) | ( ( game.outcome == sp.int(1) ) & ( bet_by_user.team_b > sp.tez(0) ) ) | ( ( game.outcome == sp.int(2) ) & ( bet_by_user.tie > sp.tez(0) ) ), message = "Error: you have lost your bet! :(")

        amount_to_send = sp.local("amount_to_send", sp.tez(0))

        sp.if game.outcome == sp.int(0):
            amount_to_send.value = sp.split_tokens(bet_by_user.team_a, sp.utils.mutez_to_nat(game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.team_a))
            bet_by_user.team_a = sp.tez(0)
        sp.if game.outcome == sp.int(1):
            amount_to_send.value = sp.split_tokens(bet_by_user.team_b, sp.utils.mutez_to_nat(game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.team_b))
            bet_by_user.team_b = sp.tez(0)         
        sp.if game.outcome == sp.int(2):
            amount_to_send.value = sp.split_tokens(bet_by_user.tie, sp.utils.mutez_to_nat(game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.tie))
            bet_by_user.tie = sp.tez(0)

        sp.send(sp.sender, amount_to_send.value)
        game.redeemed += 1  

        sp.if (bet_by_user.team_a == sp.mutez(0)) & (bet_by_user.team_b == sp.tez(0)) & (bet_by_user.tie == sp.tez(0)):
            del game.bet_amount_by_user[sp.sender]

        sp.if (game.outcome == sp.int(0)) & (game.redeemed == game.bets_by_choice.team_a):
            del self.data.games[params.game_id]
        sp.else:
            sp.if (game.outcome == sp.int(1)) & (game.redeemed == game.bets_by_choice.team_b):
                del self.data.games[params.game_id]
            sp.else:
                sp.if (game.outcome == sp.int(2)) & (game.redeemed == game.bets_by_choice.tie):
                    del self.data.games[params.game_id]

@sp.add_test(name = "Test Match Contract")
def test():
    scenario = sp.test_scenario()
    admin = sp.test_account("Admin")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    gabriel = sp.test_account("Gabriel")
    eloi = sp.test_account("Eloi")
    pierre_antoine = sp.test_account("Pierre-Antoine")
    victor = sp.test_account("Victor")
    jean_francois = sp.test_account("Jean-Francois")
    mathis = sp.test_account("Mathis")
    enguerrand = sp.test_account("Enguerrand")

    factory = SoccerBetFactory(admin.address)
    scenario += factory
    scenario.h1("Testing game initialization")
    game1 = "game1"
    scenario += factory.new_game(sp.record(
        game_id = game1,
        team_a = "France",
        team_b = "Angleterre"
    )).run(sender = admin)

    game2 = "game2"
    scenario += factory.new_game(sp.record(
        game_id = game2,
        team_a = "Nice",
        team_b = "Marseille"
    )).run(sender = admin)

    scenario.h1("Testing bet placing")

    scenario += factory.add_bet(sp.record(
        game_id = game1,
        choice = 0,
    )).run(sender = alice.address, amount = sp.tez(100))

    scenario += factory.add_bet(sp.record(
        game_id = game1,
        choice = 1,
    )).run(sender = mathis.address, amount = sp.tez(1000))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 1,
    )).run(sender = mathis.address, amount = sp.tez(7500))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 2,
    )).run(sender = enguerrand.address, amount = sp.tez(500))

    scenario += factory.add_bet(sp.record(
        game_id = game1,
        choice = 0,
    )).run(sender = pierre_antoine.address, amount = sp.tez(2000))

    scenario += factory.add_bet(sp.record(
        game_id = game1,
        choice = 1,
    )).run(sender = victor.address, amount = sp.tez(5000))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 1,
    )).run(sender = alice.address, amount = sp.tez(1000))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 1,
    )).run(sender = bob.address, amount = sp.tez(1000))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 2,
    )).run(sender = bob.address, amount = sp.tez(2000))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 0,
    )).run(sender = gabriel.address, amount = sp.tez(10000))

    scenario.h1("Testing bet removal")

    scenario += factory.remove_bet(sp.record(
        game_id = game2,
        choice = 1,
    )).run(sender = bob.address)

    scenario.h1("Testing states")

    scenario += factory.next_status(sp.record(
        game_id = game1
    )).run(sender = admin.address)

    scenario += factory.set_outcome(sp.record(
        game_id = game1,
        choice = 1,
    )).run(sender = admin.address)

    scenario += factory.next_status(sp.record(
        game_id = game1
    )).run(sender = admin.address)

    scenario += factory.next_status(sp.record(
        game_id = game2
    )).run(sender = admin.address)

    scenario += factory.set_outcome(sp.record(
        game_id = game2,
        choice = 1,
    )).run(sender = admin.address)

    scenario += factory.next_status(sp.record(
        game_id = game2
    )).run(sender = admin.address)

    scenario.h1("Testing gain redemption")

    # These scenarios are supposed to fail
    scenario += factory.redeem_tez(sp.record(
        game_id = game1
    )).run(sender = alice.address, valid = False)

    scenario += factory.redeem_tez(sp.record(
        game_id = game2
    )).run(sender = pierre_antoine.address, valid=False) 

    scenario += factory.redeem_tez(sp.record(
        game_id = game1
    )).run(sender = mathis.address)

    scenario += factory.redeem_tez(sp.record(
        game_id = game1
    )).run(sender = victor.address)

    scenario += factory.redeem_tez(sp.record(
        game_id = game2
    )).run(sender = alice.address)

    scenario += factory.redeem_tez(sp.record(
        game_id = game2
    )).run(sender = mathis.address) 