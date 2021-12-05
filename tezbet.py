

import smartpy as sp


class Bets(sp.Contract):
    # this class contains information needed for bets

    def __init__(self, id, name, team_A, team_B,
                 sum_bet_on_A, sum_bet_on_B, sum_bet_on_tie, total_sum, precision):

        self.init(

            match_id=id,
            name=name,
            team_A=team_A,
            team_B=team_B,
            rating_A=sp.pair(sp.nat(1), sp.mutez(0)),
            rating_B=sp.pair(sp.nat(1), sp.mutez(0)),
            rating_tie=sp.pair(sp.nat(1), sp.mutez(0)),
            map_better_A=sp.map(l={}, tkey=sp.TAddress, tvalue=sp.TMutez),
            map_better_B=sp.map(l={}, tkey=sp.TAddress, tvalue=sp.TMutez),
            map_better_tie=sp.map(l={}, tkey=sp.TAddress, tvalue=sp.TMutez),
            sum_bet_on_A=sum_bet_on_A,
            sum_bet_on_B=sum_bet_on_B,
            sum_bet_on_tie=sum_bet_on_tie,
            total_sum=total_sum,
            match_outcome=sp.nat(0),
            map_better_outcome=sp.map(
                l={}, tkey=sp.TAddress, tvalue=sp.TMutez),
            precision=precision

        )

    def has_bet(self):
        return(self.data.map_better_A.contains(sp.sender) | self.data.map_better_B.contains(sp.sender) | self.data.map_better_tie.contains(sp.sender))

    @sp.entry_point
    def set_outcome(self, outcome):
        self.data.match_outcome = outcome
        sp.if self.data.match_outcome == 1:
            self.data.map_better_outcome = self.data.map_better_A

        sp.if self.data.match_outcome == 2:
            self.data.map_better_outcome = self.data.map_better_B

        sp.if self.data.match_outcome == 3:
            self.data.map_better_outcome = self.data.map_better_tie

    @sp.entry_point
    def bet_on_A(self):
        condition = self.has_bet()

        sp.if ~condition:
            self.data.map_better_A[sp.sender] = sp.amount
            self.data.sum_bet_on_A += sp.amount

        sp.else:
            old_amount = self.data.map_better_A[sp.sender]
            self.data.map_better_A[sp.sender] = old_amount + sp.amount
            self.data.sum_bet_on_A += sp.amount

    @sp.entry_point
    def bet_on_B(self):
        condition = self.has_bet()

        sp.if ~condition:
            self.data.map_better_B[sp.sender] = sp.amount
            self.data.sum_bet_on_B += sp.amount

        sp.else:
            old_amount = self.data.map_better_B[sp.sender]
            self.data.map_better_B[sp.sender] = old_amount + sp.amount
            self.data.sum_bet_on_B += sp.amount

    @sp.entry_point
    def bet_on_tie(self):
        condition = self.has_bet()

        sp.if ~condition:
            self.data.map_better_tie[sp.sender] = sp.amount
            self.data.sum_bet_on_tie += sp.amount

        sp.else:
            old_amount = self.data.map_better_tie[sp.sender]
            self.data.map_better_tie[sp.sender] = old_amount + sp.amount
            self.data.sum_bet_on_tie += sp.amount

    @sp.entry_point
    def ratings_and_total_sum(self):
        self.data.total_sum = self.data.sum_bet_on_A + \
            self.data.sum_bet_on_B + self.data.sum_bet_on_tie
        total_sum_precision = sp.mul(self.data.total_sum, self.data.precision)

        rating_A_ = sp.ediv(total_sum_precision, self.data.sum_bet_on_A)
        rating_B_ = sp.ediv(total_sum_precision, self.data.sum_bet_on_B)
        rating_tie_ = sp.ediv(total_sum_precision, self.data.sum_bet_on_tie)
        self.data.rating_A = rating_A_.open_some()
        self.data.rating_B = rating_B_.open_some()
        self.data.rating_tie = rating_tie_.open_some()

    @sp.entry_point
    def withdraw_earnings(self):
        sp.verify(self.data.map_better_outcome.contains(
            sp.sender), message="better not in list")
        sp.if self.data.match_outcome == 1:
            amount_to_send_raw = sp.mul(
                self.data.map_better_outcome[sp.sender], sp.fst(self.data.rating_A))
            amount_to_send = sp.ediv(
                amount_to_send_raw, self.data.precision).open_some()
            sp.send(sp.sender, sp.fst(amount_to_send))
        sp.if self.data.match_outcome == 2:
            amount_to_send_raw = sp.mul(
                self.data.map_better_outcome[sp.sender], sp.fst(self.data.rating_B))
            amount_to_send = sp.ediv(
                amount_to_send_raw, self.data.precision).open_some()
            sp.send(sp.sender, sp.fst(amount_to_send))
        sp.if self.data.match_outcome == 3:
            amount_to_send_raw = sp.mul(
                self.data.map_better_outcome[sp.sender], sp.fst(self.data.rating_tie))
            amount_to_send = sp.ediv(
                amount_to_send_raw, self.data.precision).open_some()
            sp.send(sp.sender, sp.fst(amount_to_send))


@sp.add_test(name="Bets")
def test():

    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    charlie = sp.test_account("Charlie")
    rafael = sp.test_account("Rafael")

    c1 = Bets(id=sp.string("srfc"), name=" Italie-France", team_A="Italie ", team_B="France",
              sum_bet_on_A=sp.tez(0), sum_bet_on_B=sp.tez(0), sum_bet_on_tie=sp.tez(0), total_sum=sp.tez(0), precision=sp.nat(1000))

    scenario = sp.test_scenario()

    scenario += c1
    scenario.h1("adding first bet by alice")
    scenario += c1.bet_on_A().run(sender=alice, amount=sp.tez(1000))
    scenario += c1.bet_on_A().run(sender=alice, amount=sp.tez(400))
    scenario.h2("adding 2nd bet by bob")
    scenario += c1.bet_on_tie().run(sender=bob, amount=sp.tez(500))
    scenario += c1.bet_on_B().run(sender=charlie, amount=sp.tez(600))
    scenario += c1.bet_on_B().run(sender=charlie, amount=sp.tez(200))
    scenario += c1.bet_on_B().run(sender=charlie, amount=sp.tez(400))

    scenario += c1.bet_on_B().run(sender=rafael, amount=sp.tez(700))
    scenario += c1.ratings_and_total_sum().run()
    scenario += c1.set_outcome(sp.nat(2)).run()
    scenario += c1.withdraw_earnings().run(sender=alice, exception="better not in list")
    scenario += c1.withdraw_earnings().run(sender=rafael)
    scenario += c1.withdraw_earnings().run(sender=charlie)
