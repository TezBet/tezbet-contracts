

import smartpy as sp


class Bets(sp.Contract):
    # this class contains information needed for bets

    def __init__(self, id, name, team_A, team_B, rating_A, rating_B, rating_tie):

        self.init(

            match_id=id,
            name=name,
            team_A=team_A,
            team_B=team_B,
            rating_A=rating_A,
            rating_B=rating_B,
            rating_tie=rating_tie,
            map_better_A=sp.map(l={}, tkey=sp.TAddress, tvalue=sp.TMutez),
            map_better_B=sp.map(l={}, tkey=sp.TAddress, tvalue=sp.TMutez),
            map_better_tie=sp.map(l={}, tkey=sp.TAddress, tvalue=sp.TMutez)



        )

    def has_bet(self):
        return(self.data.map_better_A.contains(sp.sender))

    @sp.entry_point
    def bet_on_A(self):
        condition = self.has_bet()

        sp.if ~condition:
            self.data.map_better_A[sp.sender] = sp.amount

        sp.else:
            old_amount = self.data.map_better_A[sp.sender]
            self.data.map_better_A[sp.sender] = old_amount + sp.amount

    @sp.entry_point
    def bet_on_B(self):
        condition = self.has_bet()

        sp.if ~condition:
            self.data.map_better_B[sp.sender] = sp.amount

        sp.else:
            old_amount = self.data.map_better_B[sp.sender]
            self.data.map_better_B[sp.sender] = old_amount + sp.amount

    @sp.entry_point
    def bet_on_tie(self):
        condition = self.has_bet()

        sp.if ~condition:
            self.data.map_better_tie[sp.sender] = sp.amount

        sp.else:
            old_amount = self.data.map_better_tie[sp.sender]
            self.data.map_better_tie[sp.sender] = old_amount + sp.amount


@sp.add_test(name="Bets")
def test():

    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    charlie = sp.test_account("Charlie")

    c1 = Bets(id=sp.string("4axC4"), name=" Italie-France", team_A="Italie ",
              team_B="France", rating_A="1.5", rating_B="1.2", rating_tie="1.3")
    scenario = sp.test_scenario()

    scenario += c1
    scenario.h1("adding first bet by alice")
    scenario += c1.bet_on_A().run(sender=alice, amount=sp.mutez(2000))
    scenario += c1.bet_on_A().run(sender=alice, amount=sp.mutez(3000))
    scenario.h2("adding 2nd bet by bob")
    scenario += c1.bet_on_tie().run(sender=bob, amount=sp.mutez(4000))
