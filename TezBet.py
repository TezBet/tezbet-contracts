import smartpy as sp

class Match(sp.Contract):
    def __init__(self, contract_address):
        self.init(
            contract_address = contract_address,
            status = "Not started",
            outcome = "NA",
            total_betted_amount = sp.tez(0),
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

    # This entry point is for development purposes, we don't need to store the actual scores in our contract
    # since we can call them directly from the infer_outcome function
    @sp.entry_point
    def update_score(self, team, score):
        sp.verify_equal(self.data.status, "Playing", "Error: match must be playing to update the score")
        sp.verify_equal(sp.sender, self.data.contract_address, "Error: you are not allowed to update the score")
        self.data.score[team] = score

    @sp.entry_point
    def update_status(self, new_match_status):
        sp.verify_equal(sp.sender, self.data.contract_address, "Error: you are not allowed to update the match status")
        sp.if new_match_status in ("Playing", "Not started", "Suspended", "Ended"):
            self.data.status = new_match_status


    @sp.entry_point
    def place_bet(self, choice):
        # Before placing a bet, we make sure the match has not started
        sp.verify(self.data.status == "Not started", message = "Error: you cannot place a bet anymore")
        #sp.verify(sp.amount >= sp.tez(1), message = "Error: your bet must be higher or equal to 1 XTZ")
        sp.if self.data.tx.contains(sp.sender):
            sp.failwith("Error: you have already placed a bet, please remove it before placing a new one")
        sp.else: 
            #amount_in_mutez = sp.mul(sp.amount,1000000)
            self.data.betted_amount[choice] += sp.amount
            self.data.tx[sp.sender] = sp.record(amount = sp.amount, choice = choice)
            self.total_betted_amount = self.update_rating()

    @sp.entry_point
    def remove_bet(self):
        # Before removing a bet, we make sure the match has not started
        sp.verify(self.data.status == "Not started", message = "Error: you cannot remove your bet anymore")
        sp.if self.data.tx.contains(sp.sender):
            self.data.betted_amount[self.data.tx[sp.sender].choice] -= self.data.tx[sp.sender].amount
            # Here we will have to compute the tx fees for the bet removal
            fees = sp.mutez(0)
            sp.send(sp.sender, self.data.tx[sp.sender].amount - fees)
            del self.data.tx[sp.sender]
            self.update_rating()
        sp.else:
            sp.failwith("Error: you do not have any placed bet to remove")

    @sp.sub_entry_point
    def update_rating(self):
        self.data.total_betted_amount = self.data.betted_amount["team_a"] + self.data.betted_amount["team_b"] + self.data.betted_amount["tie"]
        sp.for key in self.data.betted_amount.keys():
            sp.if self.data.betted_amount[key] > sp.tez(0):
                offset = 1000000
                #rating = sp.ediv(self.data.total_betted_amount, self.data.betted_amount[key])

                rating = sp.ediv(sp.mul(self.data.total_betted_amount,offset), self.data.betted_amount[key])
                self.data.rating[key] = rating.open_some()
            sp.else:
                self.data.rating[key] = sp.pair(sp.nat(1), sp.tez(0))

    # This entry point is a sketch for the upcoming oracle contract -- here it only serves scenario purposes
    @sp.entry_point
    def infer_outcome(self):
        sp.verify_equal(sp.sender, self.data.contract_address, "Error: you are not allowed to update the match status")
        sp.verify(self.data.status == "Ended", "Error: you cannot call this function unless match has ended")
        sp.if self.data.score["team_a"] > self.data.score["team_b"]:
            self.data.outcome = "team_a"
        sp.if self.data.score["team_a"] < self.data.score["team_b"]:
            self.data.outcome = "team_b"
        sp.if self.data.score["team_a"] == self.data.score["team_b"]:
            self.data.outcome = "tie"
    
    # We let the users retrieve their gains themselves so they pay for this smart contract execution
    @sp.entry_point
    def redeem_tez(self):
        sp.verify_equal(self.data.status, "Ended", "Error: you cannot redeem your gains before the match has ended")
        sp.verify_equal(self.data.tx[sp.sender].choice, self.data.outcome, "Error: you have lost the bet")
        offset = 1000000
        raw_amount_to_send = sp.mul(self.data.tx[sp.sender].amount, sp.fst(self.data.rating[self.data.outcome]))
        amount_to_send = sp.ediv(raw_amount_to_send, offset).open_some()
        sp.send(sp.sender, sp.fst(amount_to_send))

@sp.add_test(name = "Test Match Contract")
def test():
    scenario = sp.test_scenario()

    # This account is here to mimick the behaviour of our smart contract.
    # A set of functions cannot be performed by anyone but the contract itself, updating the score for instance.
    contract = sp.test_account("Contract")

    test_match = Match(contract.address)
    scenario += test_match

    # Updating the score tests
    scenario += test_match.update_status("Playing").run(sender = contract.address)
    scenario.verify(test_match.data.status == "Playing")
    scenario += test_match.update_score(team = "team_a", score = sp.nat(2)).run(sender = contract.address)
    scenario += test_match.update_score(team = "team_b", score = sp.nat(1)).run(sender = contract.address)

    # Match status tests
    scenario += test_match.update_status("Suspended").run(sender = contract.address)
    scenario.verify(test_match.data.status == "Suspended")
    scenario += test_match.update_status("Not started").run(sender = contract.address)
    scenario.verify(test_match.data.status == "Not started")

    bob = sp.test_account("Bob")
    alice = sp.test_account("Alice")
    garfield = sp.test_account("Garfield")
    scenario += test_match.update_status("Suspended").run(valid = False, sender = bob.address)
    scenario.verify(test_match.data.status != "Suspended")
    
    # Placing and removing bets tests
    scenario += test_match.place_bet("team_a").run(sender = bob.address, amount = sp.mutez(7500))
    scenario += test_match.place_bet("team_a").run(sender = alice.address, amount = sp.mutez(5000))
    scenario += test_match.remove_bet().run(sender = bob.address)
    scenario.verify(test_match.data.betted_amount["team_a"] == sp.mutez(5000))
    scenario.verify(test_match.data.total_betted_amount == sp.mutez(5000))
    scenario += test_match.place_bet("team_b").run(sender = bob.address, amount = sp.mutez(23))
    scenario += test_match.place_bet("tie").run(sender = garfield.address, amount = sp.mutez(784))

    # Defining outcome tests
    scenario += test_match.update_status("Ended").run(sender = contract.address)
    scenario += test_match.infer_outcome().run(sender = contract.address)
    scenario.verify(test_match.data.outcome == "team_a")

    # Sending XTZ tests
    scenario += test_match.redeem_tez().run(sender = alice.address)
    scenario += test_match.update_status("Started").run(sender = contract.address)


