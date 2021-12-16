import smartpy as sp


class SoccerBetFactory(sp.Contract):
    def __init__(self, admin):
        self.init(
            admin=admin,
            games=sp.map(tkey=sp.TInt),
            archived_games = sp.map(tkey = sp.TInt),
            leaderboard=sp.map(
                tkey=sp.TInt, tvalue=sp.TRecord(better_address=sp.TAddress, amount_tx=sp.TMutez, game_id=sp.TInt))    
        )

    def insert_in_leaderboard(self, record_to_insert):
        sp.verify(self.data.games.contains(record_to_insert.game_id))

        leaderboard_len = sp.to_int(sp.len(self.data.leaderboard))
        insertion_rank = sp.local("insertion_rank", leaderboard_len)
     # course starting from the largest index
        sp.while (insertion_rank.value > 0) & (record_to_insert.amount_tx > self.data.leaderboard[insertion_rank.value - 1].amount_tx):
            self.data.leaderboard[insertion_rank.value] = self.data.leaderboard[insertion_rank.value - 1]
            insertion_rank.value -= 1
        sp.if insertion_rank.value < 10:
            self.data.leaderboard[insertion_rank.value] = record_to_insert
        

        length = sp.local("length", sp.to_int(sp.len(self.data.leaderboard)))
        sp.if (length.value >= 10):
            sp.while length.value >= 10:
                del self.data.leaderboard[length.value]
                length.value -=1

    @sp.entry_point
    def new_game(self, params):
        sp.verify_equal(sp.sender, self.data.admin,
                        message="Error: you cannot initialize a new game")
        sp.verify(~ self.data.games.contains(params.game_id))

        self.data.games[params.game_id] = sp.record(
            team_a=params.team_a,
            team_b=params.team_b,
            status=sp.int(0),
            match_timestamp = params.match_timestamp,
            outcome=sp.int(-1),
            total_bet_amount=sp.tez(0),
            bet_amount_on=sp.record(team_a=sp.tez(
                0), team_b=sp.tez(0), tie=sp.tez(0)),
            redeemed=sp.int(0),
            bets_by_choice=sp.record(team_a=sp.int(
                0), team_b=sp.int(0), tie=sp.int(0)),
            bet_amount_by_user=sp.map(
                tkey=sp.TAddress,
                tvalue=sp.TRecord(team_a=sp.TMutez,
                                  team_b=sp.TMutez, tie=sp.TMutez)
            
            )
        )

    @sp.entry_point
    def bet_on_team_a(self, game_id):
        self.add_bet(sp.record(game_id=game_id, choice=sp.int(0)))

    @sp.entry_point
    def bet_on_team_b(self, game_id):
        self.add_bet(sp.record(game_id=game_id, choice=sp.int(1)))

    @sp.entry_point
    def bet_on_tie(self, game_id):
        self.add_bet(sp.record(game_id=game_id, choice=sp.int(2)))

    @sp.private_lambda(with_storage="read-write", with_operations=False, wrap_call=True)
    def add_bet(self, params):
         
        sp.verify(self.data.games.contains(params.game_id))
        game = self.data.games[params.game_id]

        
        sp.verify((sp.now < game.match_timestamp) | (sp.timestamp_from_utc_now() < game.match_timestamp),
             message = "Error, you cannot place a bet anymore") 


        sp.verify(sp.amount >= sp.mutez(100000),
                  message="Error: your bet must be equal or higher than 0.1 XTZ")

        sp.if ~game.bet_amount_by_user.contains(sp.sender):
            game.bet_amount_by_user[sp.sender] = sp.record(
                team_a=sp.tez(0),
                team_b=sp.tez(0),
                tie=sp.tez(0))

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

        game.total_bet_amount = game.bet_amount_on.team_a + \
            game.bet_amount_on.team_b + game.bet_amount_on.tie

    @sp.entry_point
    def unbet_on_team_a(self, game_id):
        self.remove_bet(sp.record(game_id=game_id, choice=sp.int(0)))

    @sp.entry_point
    def unbet_on_team_b(self, game_id):
        self.remove_bet(sp.record(game_id=game_id, choice=sp.int(1)))

    @sp.entry_point
    def unbet_on_tie(self, game_id):
        self.remove_bet(sp.record(game_id=game_id, choice=sp.int(2)))

    @sp.private_lambda(with_storage="read-write", with_operations=True, wrap_call=True)
    def remove_bet(self, params):
        sp.verify(self.data.games.contains(params.game_id),
                  message="Error: this match does not exist")
        game = self.data.games[params.game_id]
        sp.verify(game.bet_amount_by_user.contains(sp.sender),
                  message="Error: you do not have any bets to remove")
        sp.verify( (sp.now < game.match_timestamp) | (sp.timestamp_from_utc_now() < game.match_timestamp), 
            message = "Error, you cannot remove a bet anymore")


        amount_to_send = sp.local("amount_to_send", sp.tez(0))
        

        bet_by_user = game.bet_amount_by_user[sp.sender]
        fees = sp.mutez(0)
        sp.if params.choice == 0:
            sp.verify(bet_by_user.team_a > sp.tez(
                0), message="Error: you have not placed any bets on this outcome")
            game.bet_amount_on.team_a -= bet_by_user.team_a
            amount_to_send.value = bet_by_user.team_a
            self.data.games[params.game_id].bets_by_choice.team_a -= sp.int(1)
            bet_by_user.team_a = sp.tez(0)

        sp.if params.choice == 1:
            sp.verify(bet_by_user.team_b > sp.tez(
                0), message="Error: you have not placed any bets on this outcome")
            game.bet_amount_on.team_b -= bet_by_user.team_b
            amount_to_send.value = bet_by_user.team_b
            self.data.games[params.game_id].bets_by_choice.team_b -= sp.int(1)
            bet_by_user.team_b = sp.tez(0)

        sp.if params.choice == 2:
            sp.verify(bet_by_user.tie > sp.tez(
                0), message="Error: you have not placed any bets on this outcome")
            game.bet_amount_on.tie -= bet_by_user.tie
            amount_to_send.value = bet_by_user.tie
            self.data.games[params.game_id].bets_by_choice.tie -= sp.int(1)
            bet_by_user.tie = sp.tez(0)

        sp.send(sp.sender, amount_to_send.value - fees)
        game.total_bet_amount = game.bet_amount_on.team_a + \
            game.bet_amount_on.team_b + game.bet_amount_on.tie

        sp.if (bet_by_user.team_a == sp.mutez(0)) & (bet_by_user.team_b == sp.tez(0)) & (bet_by_user.tie == sp.tez(0)):
            del game.bet_amount_by_user[sp.sender]

    @sp.private_lambda(with_storage="read-write", with_operations=False, wrap_call=True)
    def archive_game(self, params):
        sp.verify(self.data.games.contains(params.game_id), message = "Error: this match does not exist")
        game = self.data.games[params.game_id]
        sp.verify(game.outcome!=-1, message = "Error: current game is already archived")
        self.data.archived_games[params.game_id] = game


    @sp.entry_point
    def redeem_tez(self, game_id):
        sp.verify(self.data.games.contains(game_id),
                  message="Error: this match does not exist anymore!")
        game = self.data.games[game_id]
        sp.verify(game.bet_amount_by_user.contains(sp.sender),
                  message="Error: you did not place a bet on this match")
        sp.verify(game.outcome != -1, 
                  message = "Error, you cannot redeem your winnings yet")
        bet_by_user = game.bet_amount_by_user[sp.sender]
        sp.verify(((game.outcome == sp.int(0)) & (bet_by_user.team_a > sp.tez(0))) | ((game.outcome == sp.int(1)) & (bet_by_user.team_b > sp.tez(
            0))) | ((game.outcome == sp.int(2)) & (bet_by_user.tie > sp.tez(0))), message="Error: you have lost your bet! :(")

        amount_to_send = sp.local("amount_to_send", sp.tez(0))

        sp.if game.outcome == sp.int(0):
            amount_to_send.value = sp.split_tokens(bet_by_user.team_a, sp.utils.mutez_to_nat(
                game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.team_a))
            bet_by_user.team_a = sp.tez(0)
        sp.if game.outcome == sp.int(1):
            amount_to_send.value = sp.split_tokens(bet_by_user.team_b, sp.utils.mutez_to_nat(
                game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.team_b))
            bet_by_user.team_b = sp.tez(0)
        sp.if game.outcome == sp.int(2):
            amount_to_send.value = sp.split_tokens(bet_by_user.tie, sp.utils.mutez_to_nat(
                game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.tie))
            bet_by_user.tie = sp.tez(0)

        self.insert_in_leaderboard(sp.record(
            better_address=sp.sender, amount_tx=amount_to_send.value, game_id=game_id))

        sp.send(sp.sender, amount_to_send.value)
        game.redeemed += 1

        sp.if (bet_by_user.team_a == sp.mutez(0)) & (bet_by_user.team_b == sp.tez(0)) & (bet_by_user.tie == sp.tez(0)):
            del game.bet_amount_by_user[sp.sender]

        sp.if (game.outcome == sp.int(0)) & (game.redeemed == game.bets_by_choice.team_a):
            del self.data.games[game_id]
        sp.else:
            sp.if (game.outcome == sp.int(1)) & (game.redeemed == game.bets_by_choice.team_b):
                del self.data.games[game_id]
            sp.else:



                sp.if (game.outcome == sp.int(2)) & (game.redeemed == game.bets_by_choice.tie):
                    del self.data.games[game_id]

    # Below entry points mimick the future oracle behaviour and are not meant to stay
    
    @sp.entry_point
    def set_outcome(self, params):
        sp.verify_equal(self.data.games[params.game_id].outcome, -1, "Error: curent game outcome has already been set")
        sp.verify_equal(sp.sender, self.data.admin, message = "Error: you cannot update the game status")
        sp.verify((params.choice == 0) | (params.choice == 1) | (params.choice == 2), message = "Error: entered value must be comprised within {0;1;2}")
        sp.verify(self.data.games.contains(params.game_id), message = "Error: this match does not exist")

        game = self.data.games[params.game_id]
        sp.verify((sp.timestamp_from_utc_now() > game.match_timestamp) | (sp.now > game.match_timestamp),
             message = "Error, match has not started yet") 
        
        game.outcome = params.choice
        self.archive_game(params)
    # Above entry points mimick the future oracle behaviour and are not meant to stay


@sp.add_test(name="Test Match Contract")
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
    hennequin = sp.test_account("Hennequin")
    berger = sp.test_account("Berger")
    levillain = sp.test_account("Levillain")
    olivier = sp.test_account("Olivier")
    pascal = sp.test_account("Pascal") 

    factory = SoccerBetFactory(admin.address)
    scenario += factory
    scenario.h1("Testing game initialization")
    game1 = 1
    scenario += factory.new_game(sp.record(
        game_id=game1,
        team_a="France",
        team_b="Angleterre",
        match_timestamp = sp.timestamp_from_utc(2022, 1, 1, 1, 1, 1)


    )).run(sender=admin)

    game2 = 2
    scenario += factory.new_game(sp.record(
        game_id=game2,
        team_a="Nice",
        team_b="Marseille",
        match_timestamp = sp.timestamp_from_utc(2022, 1, 1, 1, 1, 1)


    )).run(sender=admin)

    game3 = 3
    scenario += factory.new_game(sp.record(
        game_id=game3,
        team_a="Lorient",
        team_b="Vannes",
        match_timestamp = sp.timestamp_from_utc(2020, 1, 1, 1, 1, 1)


    )).run(sender=admin)

    scenario.h1("Testing bet placing")

    #game 1 and 2 

    
    scenario += factory.bet_on_team_a(game1).run(
        sender=alice.address, amount=sp.tez(100))

    scenario += factory.bet_on_team_b(game1).run(
        sender=mathis.address, amount=sp.tez(1000))

    scenario += factory.bet_on_team_b(game2).run(
        sender=mathis.address, amount=sp.tez(7500))

    scenario += factory.bet_on_team_b(game2).run(
        sender=enguerrand.address, amount=sp.tez(500))

    scenario += factory.bet_on_team_a(game1).run(
        sender=pierre_antoine.address, amount=sp.tez(2000))

    scenario += factory.bet_on_team_b(game1).run(
        sender=victor.address, amount=sp.tez(5000))

    scenario += factory.bet_on_team_b(game2).run(
        sender=alice.address, amount=sp.tez(1000))

    scenario += factory.bet_on_team_b(game2).run(
        sender=bob.address, amount=sp.tez(1000))

    scenario += factory.bet_on_tie(game2).run(
        sender=bob.address,amount=sp.tez(2000))

    scenario += factory.bet_on_team_a(game2).run(
        sender=gabriel.address, amount=sp.tez(10000))

        #game3

    scenario += factory.bet_on_team_a(game3).run(
        sender = alice.address, amount=sp.tez(3000), now = sp.timestamp(1546297200))
    
    scenario += factory.bet_on_team_b(game3).run(
        sender = bob.address, amount = sp.tez(1000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_b(game3).run(
        sender = eloi.address, amount = sp.tez(2000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = gabriel.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = levillain.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))


    scenario += factory.bet_on_team_a(game3).run(
        sender = pascal.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = olivier.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    # Testing an outcome cannot be set twice
    scenario += factory.set_outcome(sp.record(
        game_id = game1,
        choice = 2,
    )).run(sender = admin.address, valid=False)

    scenario += factory.bet_on_team_a(game3).run(
        sender = hennequin.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = berger.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = enguerrand.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = victor.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = jean_francois.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = mathis.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario += factory.bet_on_team_a(game3).run(
        sender = pierre_antoine.address, amount = sp.tez(4000), now = sp.timestamp(1546297200))

    scenario.h1("Testing bet removal")

    scenario += factory.unbet_on_team_b(game2).run(sender=bob.address)

    scenario.h1("Testing outcome")
    
    scenario += factory.set_outcome(sp.record(
        game_id=game3,
        choice=0,
    )).run(sender=admin.address)
 
    scenario.h1("Testing winnings withdrawal ")

    # These scenarios aren't supposed to fail
    scenario += factory.redeem_tez(game3).run(sender=alice.address)

    scenario += factory.redeem_tez(game3).run(sender=gabriel.address)

    scenario += factory.redeem_tez(game3).run(sender=victor.address)

    scenario += factory.redeem_tez(game3).run(sender=enguerrand.address)

    scenario += factory.redeem_tez(game3).run(sender=jean_francois.address)

    scenario += factory.redeem_tez(game3).run(sender=pierre_antoine.address)

    scenario += factory.redeem_tez(game3).run(sender=berger.address)

    scenario += factory.redeem_tez(game3).run(sender=pascal.address)


    scenario += factory.redeem_tez(game3).run(sender=hennequin.address)

    scenario += factory.redeem_tez(game3).run(sender=levillain.address)

    scenario += factory.redeem_tez(game3).run(sender=mathis.address)

    # These scenarios are supposed to fail
    scenario += factory.redeem_tez(game1).run(sender=alice.address, valid=False)

    scenario += factory.redeem_tez(game2).run(sender=pierre_antoine.address, valid=False)

    scenario += factory.redeem_tez(game1).run(sender=mathis.address, valid=False)

    scenario += factory.redeem_tez(game1).run(sender=victor.address, valid=False)

    scenario += factory.redeem_tez(game2).run(sender=alice.address, valid=False)

    scenario += factory.redeem_tez(game2).run(sender=mathis.address, valid=False)

    scenario.h1("Placing bet but match has already started")

    scenario += factory.bet_on_team_a(game3).run(
        sender=alice.address, amount=sp.tez(100), now = sp.timestamp(1640991600), valid=False)

    scenario += factory.bet_on_team_b(game3).run(
        sender=bob.address, amount=sp.tez(200), now = sp.timestamp(1640991600), valid=False)

    scenario += factory.bet_on_tie(game3).run(
        sender=eloi.address, amount=sp.tez(600), now = sp.timestamp(1640991600), valid=False)

    scenario.h1("Setting outcome but match has not started")

    scenario += factory.set_outcome(sp.record(
        game_id=game2,
        choice=2,
    )).run(sender=admin.address, valid=False)

    scenario += factory.set_outcome(sp.record(
        game_id=game1,
        choice=2,
    )).run(sender=admin.address, valid=False)

    # Testing leaderboard length
    scenario.verify(sp.len(factory.data.leaderboard) <= 10)

    # Testing that leaderboard's values are ranked from highest to lowest")
    scenario.verify(factory.data.leaderboard[0] >= factory.data.leaderboard[sp.to_int(sp.len(factory.data.leaderboard))-1] )
 

 
