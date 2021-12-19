import smartpy as sp

class SoccerBetFactory(sp.Contract):
    def __init__(self, admin):
        self.init(
            admin=admin,
            games=sp.map(tkey=sp.TInt),
            archived_games = sp.map(tkey = sp.TInt),
            remainder=sp.tez(0)
        )

    @sp.entry_point
    def new_game(self, params):
        sp.verify_equal(sp.sender, self.data.admin,message="Error: you cannot initialize a new game")
        sp.verify(~ self.data.games.contains(params.game_id),message="Error: this game id already exists")

        self.data.games[params.game_id] = sp.record(
            team_a=params.team_a,
            team_b=params.team_b,
            status=sp.int(0),
            match_timestamp = params.match_timestamp,
            outcome=sp.int(-1),
            total_bet_amount=sp.tez(0),
            bet_amount_on=sp.record(team_a=sp.tez(0), team_b=sp.tez(0), tie=sp.tez(0)),
            redeemed=sp.int(0),
            bets_by_choice=sp.record(team_a=sp.int(0), team_b=sp.int(0), tie=sp.int(0)),
            bet_amount_by_user=sp.map(tkey=sp.TAddress, tvalue=sp.TRecord(timestamp=sp.TTimestamp,team_a=sp.TMutez,team_b=sp.TMutez, tie=sp.TMutez)),
            jackpot=sp.tez(0)
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
        sp.verify(sp.now < game.match_timestamp,message = "Error, you cannot place a bet anymore") 
        bet_by_user=game.bet_amount_by_user[sp.sender]

        sp.if ~game.bet_amount_by_user.contains(sp.sender):
            game.bet_amount_by_user[sp.sender] = sp.record(
                timestamp=sp.now,
                team_a=sp.tez(0),
                team_b=sp.tez(0),
                tie=sp.tez(0))
        
        sp.if params.choice == 0:
            bet_by_user.team_a += sp.amount
            game.bet_amount_on.team_a += sp.amount
            game.bets_by_choice.team_a += sp.int(1)

        sp.if params.choice == 1:
            bet_by_user.team_b += sp.amount
            game.bet_amount_on.team_b += sp.amount
            game.bets_by_choice.team_b += sp.int(1)

        sp.if params.choice == 2:
            bet_by_user.tie += sp.amount
            game.bet_amount_on.tie += sp.amount
            game.bets_by_choice.tie += sp.int(1)
        
        game.total_bet_amount = game.bet_amount_on.team_a + game.bet_amount_on.team_b + game.bet_amount_on.tie

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
        sp.verify(self.data.games.contains(params.game_id),message="Error: this match does not exist")
        game = self.data.games[params.game_id]
        sp.verify(game.bet_amount_by_user.contains(sp.sender),message="Error: you do not have any bets to remove")
        sp.verify(sp.now < game.match_timestamp, message = "Error, you cannot remove a bet anymore")
        amount_to_send = sp.local("amount_to_send", sp.tez(0))
        bet_by_user = game.bet_amount_by_user[sp.sender]

        one_day = sp.int(86000)
        service_fee = sp.local("service_fee", sp.tez(0))
        fee_multiplier = sp.local("fee_multiplier", sp.nat(0))

        time_diff = self.data.games[params.game_id].match_timestamp - bet_by_user.timestamp
        sp.if time_diff < one_day:  
            fee_multiplier.value = sp.as_nat(20000000000000-sp.mul(23148148,time_diff))
            
        sp.if params.choice == 0:
            sp.verify(bet_by_user.team_a > sp.tez(0), message="Error: you have not placed any bets on this outcome")
            game.bet_amount_on.team_a -= bet_by_user.team_a
            amount_to_send.value = bet_by_user.team_a
            self.data.games[params.game_id].bets_by_choice.team_a -= sp.int(1)
            service_fee.value = sp.mul(fee_multiplier.value, bet_by_user.team_a)
            bet_by_user.team_a = sp.tez(0)

        sp.if params.choice == 1:
            sp.verify(bet_by_user.team_b > sp.tez(0), message="Error: you have not placed any bets on this outcome")
            game.bet_amount_on.team_b -= bet_by_user.team_b
            amount_to_send.value = bet_by_user.team_b
            self.data.games[params.game_id].bets_by_choice.team_b -= sp.int(1)
            service_fee.value = sp.mul(fee_multiplier.value, bet_by_user.team_b)
            bet_by_user.team_b = sp.tez(0)

        sp.if params.choice == 2:
            sp.verify(bet_by_user.tie > sp.tez(0), message="Error: you have not placed any bets on this outcome")
            game.bet_amount_on.tie -= bet_by_user.tie
            amount_to_send.value = bet_by_user.tie
            self.data.games[params.game_id].bets_by_choice.tie -= sp.int(1)
            service_fee.value = sp.mul(fee_multiplier.value, bet_by_user.tie)
            bet_by_user.tie = sp.tez(0)


        sp.if time_diff < one_day:  
            service_fee.value = sp.split_tokens(service_fee.value, 1, 100000000000000)
            game.jackpot+=service_fee.value

        sp.send(sp.sender, amount_to_send.value - service_fee.value)
        game.total_bet_amount = game.bet_amount_on.team_a + game.bet_amount_on.team_b + game.bet_amount_on.tie

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
        sp.verify(self.data.games.contains(game_id),message="Error: this match does not exist anymore!")
        game = self.data.games[game_id]
        sp.verify(game.bet_amount_by_user.contains(sp.sender),message="Error: you did not place a bet on this match")
        sp.verify(game.outcome != -1, message = "Error, you cannot redeem your winnings yet")
        bet_by_user = game.bet_amount_by_user[sp.sender]
        total_bet_by_user=bet_by_user.team_a + bet_by_user.team_b + bet_by_user.tie
        sp.verify((game.outcome == sp.int(10)) | ((game.outcome == sp.int(0)) & (bet_by_user.team_a > sp.tez(0))) | ((game.outcome == sp.int(1)) & (bet_by_user.team_b > sp.tez(0))) | ((game.outcome == sp.int(2)) & (bet_by_user.tie > sp.tez(0))), message="Error: you have lost your bet! :(")

        amount_to_send = sp.local("amount_to_send", sp.tez(0))
        jackpot_share = sp.local("jackpot_share", sp.tez(0))
        repayment_allowed=sp.bool(False)

        # If a game is postponed or delayed, each player gets his money back
        sp.if game.outcome == sp.int(10):
            amount_to_send.value = bet_by_user.team_a + bet_by_user.team_b + bet_by_user.tie
            jackpot_share.value+=sp.split_tokens(game.jackpot,sp.utils.mutez_to_nat(bet_by_user.team_a+bet_by_user.team_b+bet_by_user.tie),sp.utils.mutez_to_nat(game.total_bet_amount))
            bet_by_user.team_a = sp.tez(0)
            bet_by_user.team_b = sp.tez(0)
            bet_by_user.tie = sp.tez(0)

        sp.if game.outcome == sp.int(0):
            sp.if game.bet_amount_on.team_a>sp.tez(0):
                amount_to_send.value = sp.split_tokens(bet_by_user.team_a, sp.utils.mutez_to_nat(game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.team_a))
                jackpot_share.value+=sp.split_tokens(game.jackpot,sp.utils.mutez_to_nat(bet_by_user.team_a),sp.utils.mutez_to_nat(game.bet_amount_on.team_a))
                bet_by_user.team_a = sp.tez(0)            
            sp.else:
                amount_to_send.value=total_bet_by_user
                jackpot_share.value+=sp.split_tokens(game.jackpot,sp.utils.mutez_to_nat(total_bet_by_user),sp.utils.mutez_to_nat(game.total_bet_amount))
                bet_by_user.team_b=sp.tez(0)  
                bet_by_user.tie=sp.tez(0)
                repayment_allowed=True

        sp.if game.outcome == sp.int(1):
            sp.if game.bet_amount_on.team_b>sp.tez(0):
                amount_to_send.value = sp.split_tokens(bet_by_user.team_b, sp.utils.mutez_to_nat(game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.team_b))
                jackpot_share.value+=sp.split_tokens(game.jackpot,sp.utils.mutez_to_nat(bet_by_user.team_b),sp.utils.mutez_to_nat(game.bet_amount_on.team_b))
                bet_by_user.team_b = sp.tez(0)
            sp.else:
                amount_to_send.value=total_bet_by_user
                jackpot_share.value+=sp.split_tokens(game.jackpot,sp.utils.mutez_to_nat(total_bet_by_user),sp.utils.mutez_to_nat(game.total_bet_amount))
                bet_by_user.team_a=sp.tez(0)  
                bet_by_user.tie=sp.tez(0)
                repayment_allowed=True

        sp.if game.outcome == sp.int(2):
            sp.if game.bet_amount_on.tie>sp.tez(0):
                amount_to_send.value = sp.split_tokens(bet_by_user.tie, sp.utils.mutez_to_nat(game.total_bet_amount), sp.utils.mutez_to_nat(game.bet_amount_on.tie))
                jackpot_share.value+=sp.split_tokens(game.jackpot,sp.utils.mutez_to_nat(bet_by_user.tie),sp.utils.mutez_to_nat(game.bet_amount_on.tie))
                bet_by_user.tie = sp.tez(0)
            sp.else:
                amount_to_send.value=total_bet_by_user
                jackpot_share.value+=sp.split_tokens(game.jackpot,sp.utils.mutez_to_nat(total_bet_by_user),sp.utils.mutez_to_nat(game.total_bet_amount))
                bet_by_user.team_a=sp.tez(0)  
                bet_by_user.team_b=sp.tez(0)
                repayment_allowed=True
        
        game.jackpot-=jackpot_share.value
        sp.send(sp.sender, amount_to_send.value+jackpot_share.value)
        game.redeemed += 1

        sp.if (bet_by_user.team_a == sp.mutez(0)) & (bet_by_user.team_b == sp.tez(0)) & (bet_by_user.tie == sp.tez(0)):
            del game.bet_amount_by_user[sp.sender]

        sp.if repayment_allowed==False:
            sp.if (game.outcome == sp.int(0)) & (game.redeemed == game.bets_by_choice.team_a):
                del self.data.games[game_id]
            sp.else:
                sp.if (game.outcome == sp.int(1)) & (game.redeemed == game.bets_by_choice.team_b):
                    del self.data.games[game_id]
                sp.else:
                    sp.if (game.outcome == sp.int(2)) & (game.redeemed == game.bets_by_choice.tie):
                        del self.data.games[game_id]
        sp.else:
            sp.if sp.len(game.bet_amount_by_user)==0:
                del self.data.games[game_id]

    # Below entry points mimick the future oracle behaviour and are not meant to stay
    @sp.entry_point
    def set_outcome(self, params):
        sp.verify_equal(self.data.games[params.game_id].outcome, -1, "Error: current game outcome has already been set")
        sp.verify_equal(sp.sender, self.data.admin, message = "Error: you cannot update the game status")
        sp.verify((params.choice == 0) | (params.choice == 1) | (params.choice == 2) | (params.choice == 10), message = "Error: entered value must be comprised in {0;1;2}")
        sp.verify(self.data.games.contains(params.game_id), message = "Error: this match does not exist")
        game = self.data.games[params.game_id]
        sp.if params.choice != 10:
            sp.verify(sp.now > game.match_timestamp, message = "Error: match has not started yet") 
        game.outcome = params.choice
        sp.if (game.bet_amount_on.team_a == sp.tez(0)) & (game.bet_amount_on.team_b == sp.tez(0)) & (game.bet_amount_on.tie == sp.tez(0)):
            sp.if game.jackpot>sp.tez(0):
                self.data.remainder+=game.jackpot
                game.jackpot=sp.tez(0)
            del self.data.games[params.game_id]
        sp.else:
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

    game1 = 1
    factory = SoccerBetFactory(admin.address)
    scenario += factory
    scenario.h1("Testing game initialization")
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
        match_timestamp = sp.timestamp_from_utc(2022, 1, 1, 1, 1, 1)
    )).run(sender=admin)

    game5 = 5
    scenario += factory.new_game(sp.record(
        game_id=game5,
        team_a="Olympique Lyonnais",
        team_b="PSG",
        match_timestamp = sp.timestamp_from_utc(2022, 1, 1, 1, 1, 1)
    )).run(sender=admin)

    game6 = 6
    scenario += factory.new_game(sp.record(
        game_id=game6,
        team_a="Luxembourg",
        team_b="Malte",
        match_timestamp = sp.timestamp_from_utc(2022, 1, 1, 1, 1, 1)
    )).run(sender=admin)

    game7 = 7
    scenario += factory.new_game(sp.record(
        game_id=game7,
        team_a="Irlande",
        team_b="Ecosse",
        match_timestamp = sp.timestamp_from_utc(2022, 1, 1, 1, 1, 40)
    )).run(sender=admin)

    game8 = 8
    scenario += factory.new_game(sp.record(
        game_id=game8,
        team_a="Allemagne",
        team_b="Pologne",
        match_timestamp = sp.timestamp_from_utc(2022, 1, 1, 1, 1, 3)
    )).run(sender=admin)

    scenario.h1("Testing bet placing")

    # Betting on game 1 

    scenario += factory.bet_on_team_a(game1).run(
        sender=pierre_antoine.address, amount=sp.tez(2000))

    scenario += factory.bet_on_team_b(game1).run(
        sender=victor.address, amount=sp.tez(5000))

    scenario += factory.bet_on_team_a(game1).run(sender=alice.address, amount=sp.tez(100), now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 0))

    scenario += factory.bet_on_team_b(game1).run(
        sender=mathis.address, amount=sp.tez(1000))

    scenario += factory.bet_on_tie(game1).run(
        sender=bob.address,amount=sp.tez(2000))

    # Betting on game 2

    scenario += factory.bet_on_team_b(game2).run(
        sender=mathis.address, amount=sp.tez(7500))

    scenario += factory.bet_on_team_b(game2).run(
        sender=enguerrand.address, amount=sp.tez(500))

    scenario += factory.bet_on_team_b(game2).run(
        sender=alice.address, amount=sp.tez(1000))

    scenario += factory.bet_on_team_b(game2).run(
        sender=bob.address, amount=sp.tez(1000))

    scenario += factory.bet_on_team_a(game2).run(
        sender=gabriel.address, amount=sp.tez(10000))

    # Betting on game 3

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

    # Betting on game 5

    scenario += factory.bet_on_team_b(game5).run(sender=mathis.address, amount=sp.tez(100), now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 0))

    scenario += factory.unbet_on_team_b(game5).run(sender=mathis.address)

    scenario += factory.bet_on_tie(game5).run(sender=mathis.address, amount=sp.tez(7500))

    scenario += factory.bet_on_team_a(game5).run(sender=enguerrand.address, amount=sp.tez(500))

    scenario += factory.bet_on_team_b(game5).run(sender=enguerrand.address, amount=sp.tez(2500))

    # Testing an outcome cannot be set twice
    scenario += factory.set_outcome(sp.record(
        game_id = game1,
        choice = 2,
    )).run(sender = admin.address, valid=False)

    scenario.h1("Testing bet removal")

    scenario += factory.unbet_on_tie(game1).run(sender=bob.address)

    scenario.h1("Testing outcome")

    scenario += factory.set_outcome(sp.record(game_id = game1, choice = 1)).run(sender=admin.address, now = sp.timestamp(1640998862))

    scenario += factory.set_outcome(sp.record(game_id = game2, choice = 1)).run(sender=admin.address, now = sp.timestamp(1640998862))

    # Testing the deletion of games with no bet records
    scenario += factory.set_outcome(sp.record(game_id = game6, choice = 1)).run(sender=admin.address, now = sp.timestamp(1640998862))

    # Testing cancelled/postponed outcome
    scenario += factory.set_outcome(sp.record(game_id = game5, choice = 10)).run(sender=admin.address, now = sp.timestamp(1640998862))

    scenario.h1("Testing losers can recover their bet amount when there is no bet on the actual outcome")

    # scenario += factory.bet_on_team_a(game8).run(sender=enguerrand.address, amount=sp.tez(2500), now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 1))

    # scenario += factory.set_outcome(sp.record(game_id = game8, choice = 1)).run(sender=admin.address, now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 3))

    # scenario += factory.redeem_tez(game8).run(sender=enguerrand.address, now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 4))


    scenario.h1("Testing contract's remainder increase when no-bet games are deleted")

    scenario += factory.bet_on_team_b(game7).run(sender=enguerrand.address, amount=sp.tez(2500), now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 1))

    scenario += factory.unbet_on_team_b(game7).run(sender=enguerrand.address, now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 20))

    scenario += factory.set_outcome(sp.record(game_id = game7, choice = 1)).run(sender=admin.address, now=sp.timestamp_from_utc(2022, 1, 1, 1, 1, 59))

    scenario.verify(factory.data.remainder>sp.tez(0))

    scenario.h1("Testing winnings withdrawal ")

    scenario += factory.redeem_tez(game1).run(sender=mathis.address)

    scenario += factory.redeem_tez(game1).run(sender=victor.address)

    scenario += factory.redeem_tez(game2).run(sender=alice.address)

    scenario += factory.redeem_tez(game2).run(sender=mathis.address)

    scenario += factory.redeem_tez(game2).run(sender=enguerrand.address)

    # Testing Bob can redeem a winning bet while having lost another one
    scenario += factory.redeem_tez(game2).run(sender=bob.address)

    # Testing Alice cannot redeem gains from a game she did not bet on
    scenario += factory.redeem_tez(game1).run(sender=alice.address, valid=False)

    # Testing Pierre-Antoine cannot redeem gains from a bet he lost
    scenario += factory.redeem_tez(game1).run(sender=pierre_antoine.address, valid=False)
   
    # Testing players can recover their bet amount when a game is cancelled/postponed
    scenario += factory.redeem_tez(game5).run(sender=mathis.address)

    scenario += factory.redeem_tez(game5).run(sender=enguerrand.address)

    scenario.h1("Setting outcome but match has not started")

    scenario += factory.set_outcome(sp.record(
        game_id=game2,
        choice=2,
    )).run(sender=admin.address, valid=False)

    scenario += factory.set_outcome(sp.record(
        game_id=game1,
        choice=2,
    )).run(sender=admin.address, valid=False)