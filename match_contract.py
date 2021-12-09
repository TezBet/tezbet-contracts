import smartpy as sp

class SoccerBetFactory(sp.Contract):
    def __init__(self, admin):
        self.init(
            admin = admin,
            games = sp.map(tkey = sp.TString),  
        )
    
    @sp.entry_point
    def new_game(self, params):
        sp.verify_equal(sp.sender, self.data.admin, message = "You cannot initialize a new game")
        sp.verify(~ self.data.games.contains(params.game_id))

        self.data.games[params.game_id] = sp.record(
            team_a = params.team_a,
            team_b = params.team_b,
            status = sp.int(0),
            outcome = "NA",
            total_betted_amount = sp.tez(0),
            betted_amount = sp.map({
                "team_a": sp.tez(0),
                "team_b": sp.tez(0),
                "tie": sp.tez(0)
            }),
            rating = sp.map({
                "team_a": sp.pair(sp.nat(1), sp.tez(0)),
                "team_b": sp.pair(sp.nat(1), sp.tez(0)),
                "tie": sp.pair(sp.nat(1), sp.tez(0))
            }),
            bet_amount_by_user = sp.map(
                tkey = sp.TAddress, 
                tvalue = sp.TRecord(team_a = sp.TMutez, team_b = sp.TMutez, tie = sp.TMutez)
            ),
            final_rating = sp.record(
                team_a = sp.pair(sp.nat(1), sp.mutez(0)),
                team_b = sp.pair(sp.nat(1), sp.mutez(0)),
                tie = sp.pair(sp.nat(1), sp.mutez(0))
            )
        )

    @sp.entry_point
    def add_bet(self, params):
        sp.verify(self.data.games.contains(params.game_id))
        game = self.data.games[params.game_id]

        sp.verify(game.status == 0, message = "Error: you cannot place a bet anymore")
        sp.verify(sp.amount > sp.mutez(0), message = "Error: your bet cannot be null")

        sp.if ~game.bet_amount_by_user.contains(sp.sender):
            game.bet_amount_by_user[sp.sender] = sp.record(
                team_a = sp.tez(0),
                team_b = sp.tez(0),
                tie    = sp.tez(0),
            )

        sp.if params.choice == 0:
            game.bet_amount_by_user[sp.sender].team_a += sp.amount
        sp.if params.choice == 1:
            game.bet_amount_by_user[sp.sender].team_b += sp.amount
        sp.if params.choice == 2:
            game.bet_amount_by_user[sp.sender].tie += sp.amount

    @sp.entry_point
    def remove_bet(self, params):
        sp.verify(self.data.games.contains(params.game_id))
        game = self.data.games[params.game_id]

        sp.verify(game.status == 1, message = "Error: you cannot remove your bet anymore")
        sp.verify(game.bet_amount_by_user.contains(sp.sender), message = "Error: you do not have any bets to remove")

        #game.betted_amount[self.data.tx[sp.sender].choice] -= self.data.tx[sp.sender].amount
        # Here we will have to compute the tx fees for the bet removal
        fees = sp.mutez(0)
        #sp.send(sp.sender, game.bet_amount_by_user[sp.sender].amount - fees)
        #del self.data.tx[sp.sender] 
        sp.if params.choice == 0:
            sp.verify(game.bet_amount_by_user[sp.sender].team_a > sp.tez(0))
            game.bet_amount_by_user[sp.sender].team_a -= sp.amount
        sp.if params.choice == 1:
            sp.verify(game.bet_amount_by_user[sp.sender].team_b > sp.tez(0))
            game.bet_amount_by_user[sp.sender].team_b -= sp.amount
        sp.if params.choice == 2:
            sp.verify(game.bet_amount_by_user[sp.sender].tie > sp.tez(0))
            game.bet_amount_by_user[sp.sender].tie -= sp.amount       
        
        sp.send(sp.sender, game.bet_amount_by_user[sp.sender].team_a + game.bet_amount_by_user[sp.sender].team_b + game.bet_amount_by_user[sp.sender].tie)


@sp.add_test(name = "Test Match Contract")
def test():
    scenario = sp.test_scenario()
    admin = sp.test_account("Admin")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")

    factory = SoccerBetFactory(admin.address)
    scenario += factory

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

    scenario += factory.add_bet(sp.record(
        game_id = game1,
        choice = 0,
    )).run(sender = alice.address, amount = sp.tez(100))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 1,
    )).run(sender = alice.address, amount = sp.tez(800))

    scenario += factory.add_bet(sp.record(
        game_id = game2,
        choice = 2,
    )).run(sender = bob.address, amount = sp.tez(800))