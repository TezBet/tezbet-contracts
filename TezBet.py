import smartpy as sp

class Match(sp.Contract):
    def __init__(self, manager_address):
        self.init(
            manager_address = manager_address,
            status = "Not started",
            outcome = "NA",
            total_betted_amount = sp.tez(0),
            team_names = sp.map({
                "team_a": sp.string("Team A"),
                "team_b": sp.string("Team B")
            }),
            score = sp.map({
                "team_a": sp.nat(0),
                "team_b": sp.nat(0)
            }),
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

            tx = sp.map(l = {}, tkey = sp.TAddress, tvalue = sp.TRecord(amount = sp.TMutez, choice = sp.TString))
        )

    @sp.entry_point
    def update_score(self, team, score):
        sp.verify_equal(self.data.status, "Playing", "Error: match must be playing to update the score")
        sp.verify_equal(sp.sender, self.data.manager_address, "Error: you are not allowed to update the score")
        self.data.score[team] = score

    @sp.entry_point
    def update_status(self, new_match_status):
        sp.verify_equal(sp.sender, self.data.manager_address, "Error: you are not allowed to update the match status")
        sp.if new_match_status in ("Playing", "Not started", "Suspended", "Ended"):
            self.data.status = new_match_status


    @sp.entry_point
    def place_bet(self, bet):
        sp.verify(self.data.status == "Not started", message = "Error: you cannot place a bet anymore")
        sp.verify(bet.amount > sp.tez(0), message = "Error: your bet must be higher than 0 XTZ")
        sp.if self.data.tx.contains(sp.sender):
            sp.failwith("Error: you have already placed a bet, please remove it before placing a new one")
        sp.else: 
            self.data.betted_amount[bet.choice] += bet.amount
            self.data.tx[sp.sender] = sp.record(amount = bet.amount, choice = bet.choice)
            self.total_betted_amount = self.update_rating()

    @sp.entry_point
    def remove_bet(self):
        sp.verify(self.data.status == "Not started", message = "Error: you cannot remove your bet anymore")
        sp.if self.data.tx.contains(sp.sender):
            self.data.betted_amount[self.data.tx[sp.sender].choice] -= self.data.tx[sp.sender].amount
            del self.data.tx[sp.sender]
            self.update_rating()
        sp.else:
            sp.failwith("Error: you do not have any placed bet to remove")

    @sp.sub_entry_point
    def update_rating(self):
        self.data.total_betted_amount = self.data.betted_amount["team_a"] + self.data.betted_amount["team_b"] + self.data.betted_amount["tie"]

        sp.for key in self.data.betted_amount.keys():
            sp.if self.data.betted_amount[key] > sp.tez(0):
                rating = sp.ediv(self.data.total_betted_amount, self.data.betted_amount[key])
                self.data.rating[key] = rating.open_some()
            sp.else:
                self.data.rating[key] = sp.pair(sp.nat(1), sp.tez(0))

    @sp.entry_point
    def define_outcome(self):
        sp.verify_equal(sp.sender, self.data.manager_address, "Error: you are not allowed to update the match status")
        sp.verify(self.data.status == "Ended", "Error: you cannot call this function unless match has ended")
        sp.if self.data.score["team_a"] > self.data.score["team_b"]:
            self.data.outcome = "team_a"
        sp.if self.data.score["team_a"] < self.data.score["team_b"]:
            self.data.outcome = "team_b"
        sp.if self.data.score["team_a"] == self.data.score["team_b"]:
            self.data.outcome = "tie"
        self.send_tez(self.data.outcome)
        
    @sp.sub_entry_point
    def send_tez(outcome):
        pass

@sp.add_test(name = "Test Match Contract")
def test():
    scenario = sp.test_scenario()

    admin = sp.test_account("Bookmaker")

    test_match = Match(admin.address)
    scenario += test_match

    # Updating the score tests
    scenario += test_match.update_status("Playing").run(sender = admin.address)
    scenario.verify(test_match.data.status == "Playing")
    scenario += test_match.update_score(team = "team_a", score = sp.nat(2)).run(sender = admin.address)
    scenario += test_match.update_score(team = "team_b", score = sp.nat(1)).run(sender = admin.address)

    # Match status tests
    scenario += test_match.update_status("Suspended").run(sender = admin.address)
    scenario.verify(test_match.data.status == "Suspended")
    scenario += test_match.update_status("Not started").run(sender = admin.address)
    scenario.verify(test_match.data.status == "Not started")

    bob = sp.test_account("Bob")
    alice = sp.test_account("Alice")
    garfield = sp.test_account("Garfield")
    # scenario += test_match.update_status("Suspended").run(sender = bob.address)
    # scenario.verify(test_match.data.status == "Started")
    
    # Placing and removing bets tests
    scenario += test_match.place_bet(sp.record(amount = sp.tez(1000), choice = "team_a")).run(sender = bob.address)
    scenario += test_match.place_bet(sp.record(amount = sp.tez(5000), choice = "team_a")).run(sender = alice.address)
    scenario += test_match.remove_bet().run(sender = bob.address)
    scenario.verify(test_match.data.betted_amount["team_a"] == sp.tez(5000))
    scenario.verify(test_match.data.total_betted_amount == sp.tez(5000))
    scenario += test_match.place_bet(sp.record(amount = sp.tez(10000), choice = "team_b")).run(sender = bob.address)
    scenario += test_match.place_bet(sp.record(amount = sp.tez(5000), choice = "tie")).run(sender = garfield.address)

    # Defining outcome tests
    scenario += test_match.update_status("Ended").run(sender = admin.address)
    scenario += test_match.define_outcome().run(sender = admin.address)
    scenario.verify(test_match.data.outcome == "team_a")


