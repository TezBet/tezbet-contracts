import smartpy as sp


class SoccerBetFactory(sp.Contract):
    def __init__(self, admin):
        self.init(
            admin=admin,
            games=sp.map(tkey=sp.TString),

            leaderboard=sp.map(
                tkey=sp.TInt, tvalue=sp.TRecord(better_address=sp.TAddress, amount_tx=sp.TMutez, game_id=sp.TString))


        )

    def leaderboard(self, params):
        sp.verify(self.data.games.contains(params.game_id))  # le match existe
        # type(val) = record
        # type(val) = record
        sp.if sp.len(self.data.leaderboard) == 0:
            self.data.leaderboard[0] = params
        sp.else:

            insertion_rank = sp.local("insertion_rank", sp.int(0))
            sp.while (params.amount_tx < self.data.leaderboard[insertion_rank.value].amount_tx) & (insertion_rank.value < 10):
                insertion_rank.value += 1

            j = sp.local("j", sp.to_int(sp.len(self.data.leaderboard)))
            sp.while (j.value > insertion_rank.value) & (j.value >= 0):
                self.data.leaderboard[j.value] = self.data.leaderboard[j.value-1]
                j.value -= 1
            self.data.leaderboard[insertion_rank.value] = params

    @sp.entry_point
    def new_game(self, params):
        sp.verify_equal(sp.sender, self.data.admin,
                        message="You cannot initialize a new game")
        sp.verify(~ self.data.games.contains(params.game_id))

        self.data.games[params.game_id] = sp.record(

            team_a=params.team_a,
            team_b=params.team_b,
            status=sp.int(0),
            bet_amount_by_user=sp.map(
                tkey=sp.TAddress,
                tvalue=sp.TRecord(team_a=sp.TMutez,
                                  team_b=sp.TMutez, tie=sp.TMutez)
            ),
            final_rating=sp.record(
                team_a=sp.pair(sp.nat(1), sp.mutez(0)),
                team_b=sp.pair(sp.nat(1), sp.mutez(0)),
                tie=sp.pair(sp.nat(1), sp.mutez(0))
            ),
            total=sp.tez(0)
        )

    @sp.entry_point
    def add_bet(self, params):
        sp.verify(self.data.games.contains(params.game_id))
        game = self.data.games[params.game_id]

        sp.verify(game.status == 0,
                  message="Error: you cannot place a bet anymore")
        sp.verify(sp.amount > sp.mutez(0),
                  message="Error: your bet cannot be null")

        sp.if ~game.bet_amount_by_user.contains(sp.sender):
            game.bet_amount_by_user[sp.sender] = sp.record(
                team_a=sp.tez(0),
                team_b=sp.tez(0),
                tie=sp.tez(0),
            )

        sp.if params.choice == 0:
            game.bet_amount_by_user[sp.sender].team_a += sp.amount
            self.leaderboard(sp.record(better_address=sp.sender,
                             amount_tx=sp.amount, game_id=params.game_id))

        sp.if params.choice == 1:
            game.bet_amount_by_user[sp.sender].team_b += sp.amount
            self.leaderboard(sp.record(better_address=sp.sender,
                             amount_tx=sp.amount, game_id=params.game_id))

        sp.if params.choice == 2:
            game.bet_amount_by_user[sp.sender].tie += sp.amount
            self.leaderboard(sp.record(better_address=sp.sender,
                             amount_tx=sp.amount, game_id=params.game_id))

    @sp.entry_point
    def remove_bet(self, params):
        sp.verify(self.data.games.contains(params.game_id),
                  message="You do not have any bets to remove")
        game = self.data.games[params.game_id]

        sp.verify(game.status == 0,
                  message="Error: you cannot remove your bet anymore")
        sp.verify(game.bet_amount_by_user.contains(sp.sender),
                  message="Error: you do not have any bets to remove")

        bet_by_user = game.bet_amount_by_user[sp.sender]
        # Here we will have to compute the tx fees for the bet removal
        fees = sp.mutez(0)
        sp.if params.choice == 0:
            sp.verify(bet_by_user.team_a > sp.tez(
                0), message="Error: you have not placed any bets on this outcome")
            sp.send(sp.sender, bet_by_user.team_a - fees)
            bet_by_user.team_a = sp.tez(0)
        sp.if params.choice == 1:
            sp.verify(bet_by_user.team_b > sp.tez(
                0), message="Error: you have not placed any bets on this outcome")
            sp.send(sp.sender, bet_by_user.team_b - fees)
            bet_by_user.team_b = sp.tez(0)
        sp.if params.choice == 2:
            sp.verify(bet_by_user.tie > sp.tez(
                0), message="Error: you have not placed any bets on this outcome")
            sp.send(sp.sender, bet_by_user.tie - fees)
            bet_by_user.tie = sp.tez(0)

        sp.if (bet_by_user.team_a == sp.mutez(0)) & (bet_by_user.team_b == sp.tez(0)) & (bet_by_user.tie == sp.tez(0)):
            del game.bet_amount_by_user[sp.sender]

    @sp.entry_point
    def redeem_tez(self, params):
        game = self.data.games[params.game_id]
        sp.verify(game.bet_amount_by_user.contains(sp.sender),
                  message="Error: you did not place a bet on this match")
        sp.verify_equal(game.status, sp.int(
            2), "Error: you cannot redeem your gains before the match has ended")

        bet_by_user = game.bet_amount_by_user[sp.sender]
        outcome = sp.local("outcome", sp.int(1))
        offset = 1
        raw_amount_to_send = sp.local("raw_amount_to_send", sp.tez(0))

        sp.if (outcome.value == sp.int(0)) & (bet_by_user.team_a > sp.tez(0)):
            raw_amount_to_send.value = sp.mul(
                bet_by_user.team_b, sp.fst(game.final_rating.team_b))
            bet_by_user.team_a = sp.tez(0)
            amount_to_send = sp.ediv(
                raw_amount_to_send.value, offset).open_some()
            sp.send(sp.sender, sp.fst(amount_to_send))

        sp.if (outcome.value == sp.int(1)) & (bet_by_user.team_b > sp.tez(0)):
            raw_amount_to_send.value = sp.mul(
                bet_by_user.team_b, sp.fst(game.final_rating.team_b))
            bet_by_user.team_b = sp.tez(0)
            amount_to_send = sp.ediv(
                raw_amount_to_send.value, offset).open_some()
            sp.send(sp.sender, sp.fst(amount_to_send))

        sp.if (outcome.value == sp.int(2)) & (bet_by_user.tie > sp.tez(0)):
            raw_amount_to_send.value = sp.mul(
                bet_by_user.tie, sp.fst(game.final_rating.tie))
            bet_by_user.tie = sp.tez(0)
            amount_to_send = sp.ediv(
                raw_amount_to_send.value, offset).open_some()
            sp.send(sp.sender, sp.fst(amount_to_send))

        sp.if (bet_by_user.team_a == sp.mutez(0)) & (bet_by_user.team_b == sp.tez(0)) & (bet_by_user.tie == sp.tez(0)):
            del game.bet_amount_by_user[sp.sender]

    @sp.entry_point
    def update_status(self, params):
        sp.verify_equal(sp.sender, self.data.admin,
                        message="You cannot update the game status")
        game = self.data.games[params.game_id]

        sp.if game.status == sp.int(1):
            game.status += 1
        sp.if game.status == sp.int(0):
            game.status += 1
            game.set_ratings(game)

    @sp.private_lambda(with_operations=False, with_storage="read-write", wrap_call=True)
    def set_ratings(self, game):
        sp.verify_equal(game.status, sp.int(1), "Error: ratings cannot be set")
        bet_amount_on_team_a = sp.local("bet_amount_on_team_a", sp.tez(0))
        bet_amount_on_team_b = sp.local("bet_amount_on_team_b", sp.tez(0))
        bet_amount_on_tie = sp.local("bet_amount_on_tie", sp.tez(0))
        total_bet_amount = sp.local("total_bet_amount", sp.tez(0))
        offset = 1000000

        sp.for key in game.bet_amount_by_user.keys():
            bet_amount_on_team_a.value += game.bet_amount_by_user[key].team_a
            bet_amount_on_team_b.value += game.bet_amount_by_user[key].team_b
            bet_amount_on_tie.value += game.bet_amount_by_user[key].tie

        total_bet_amount.value = sp.mul(
            bet_amount_on_team_a.value + bet_amount_on_team_b.value + bet_amount_on_tie.value, offset)
        game.total = total_bet_amount.value

        game.final_rating = sp.record(
            team_a=sp.ediv(total_bet_amount.value,
                           bet_amount_on_team_a.value).open_some(),
            team_b=sp.ediv(total_bet_amount.value,
                           bet_amount_on_team_b.value).open_some(),
            tie=sp.ediv(total_bet_amount.value,
                        bet_amount_on_tie.value).open_some()
        )


@sp.add_test(name="Test Match Contract")
def test():
    scenario = sp.test_scenario()
    admin = sp.test_account("Admin")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    garfield = sp.test_account("Gabriel")

    factory = SoccerBetFactory(admin.address)
    scenario += factory

    game1 = "game1"
    scenario += factory.new_game(sp.record(
        game_id=game1,
        team_a="France",
        team_b="Angleterre"
    )).run(sender=admin)

    game2 = "game2"
    scenario += factory.new_game(sp.record(
        game_id=game2,
        team_a="Nice",
        team_b="Marseille"
    )).run(sender=admin)

    scenario += factory.add_bet(sp.record(
        game_id=game1,
        choice=0,
    )).run(sender=alice.address, amount=sp.tez(100))

    scenario += factory.add_bet(sp.record(
        game_id=game2,
        choice=1,
    )).run(sender=alice.address, amount=sp.tez(800))

    scenario += factory.add_bet(sp.record(
        game_id=game2,
        choice=1,
    )).run(sender=bob.address, amount=sp.tez(800))

    scenario += factory.add_bet(sp.record(
        game_id=game2,
        choice=2,
    )).run(sender=bob.address, amount=sp.tez(1600))

    scenario += factory.add_bet(sp.record(
        game_id=game2,
        choice=0,
    )).run(sender=garfield.address, amount=sp.tez(3200))

    scenario += factory.remove_bet(sp.record(
        game_id=game2,
        choice=1,
    )).run(sender=bob.address)

    scenario += factory.update_status(sp.record(
        game_id=game2
    )).run(sender=admin.address)

    scenario += factory.update_status(sp.record(
        game_id=game2
    )).run(sender=admin.address)

    scenario += factory.redeem_tez(sp.record(
        game_id=game2,
        choice=1,
    )).run(sender=alice.address)

    scenario += factory.redeem_tez(sp.record(
        game_id=game2,
        choice=1,
    )).run(sender=bob.address)
