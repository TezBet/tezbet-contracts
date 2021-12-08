import smartpy as sp

class Match(sp.Contract):
    def __init__(self, teams):
        #self.init_type()
        self.init(
            status = "Not started",
            outcome = "NA",
            total_betted_amount = sp.tez(0),
            names = sp.map({
                "team_a": teams.team_a,
                "team_b": teams.team_b
            }),
            betted_amount = sp.map({
                teams.team_a: sp.tez(0),
                teams.team_b: sp.tez(0),
                "tie": sp.tez(0)
            }),
            rating = sp.map({
                teams.team_a: sp.pair(sp.nat(1), sp.tez(0)),
                teams.team_b: sp.pair(sp.nat(1), sp.tez(0)),
                "tie": sp.pair(sp.nat(1), sp.tez(0))
            }),

            tx = sp.map(l = {}, tkey = sp.TAddress, tvalue = sp.TRecord(amount = sp.TMutez, choice = sp.TString))
        )

    # This function will be called by the contract after each oracle call
    def update_score(self, team, score):
        sp.verify_equal(self.data.status, "Playing", "Error: match must be playing to update the score")
        self.data.score[team] = score

    # This function will be called by the contract after each oracle call
    def update_status(self, new_match_status):
        sp.if new_match_status in ("Playing", "Not started", "Suspended", "Ended"):
            self.data.status = new_match_status

    @sp.entry_point
    def place_bet(self, choice):
        # Before placing a bet, we make sure the match has not started
        sp.verify(self.data.status == "Not started", message = "Error: you cannot place a bet anymore")
        sp.verify(sp.amount > sp.mutez(0), message = "Error: your bet cannot be null")
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
        self.data.total_betted_amount = self.data.betted_amount[self.data.names["team_a"]] + self.data.betted_amount[self.data.names["team_b"]] + self.data.betted_amount["tie"]
        sp.for key in self.data.betted_amount.keys():
            sp.if self.data.betted_amount[key] > sp.tez(0):
                offset = 1000000
                rating = sp.ediv(sp.mul(self.data.total_betted_amount,offset), self.data.betted_amount[key])
                self.data.rating[key] = rating.open_some()
            sp.else:
                self.data.rating[key] = sp.pair(sp.nat(1), sp.tez(0))
    
    # We let the users retrieve their gains themselves so they pay for this smart contract execution
    @sp.entry_point
    def redeem_tez(self):

        # The two following lines are here for testing purposes while the oracle calls have not be set.
        self.data.status = "Ended"
        self.data.outcome = self.data.names["team_a"]

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

    test_match = Match(sp.record(team_a = "France", team_b = "Italie"))
    scenario += test_match

    bob = sp.test_account("Bob")
    alice = sp.test_account("Alice")
    p_a = sp.test_account("Pierre-Antoine")
    garfield = sp.test_account("Garfield")
    
    # Placing and removing bets tests
    scenario += test_match.place_bet("France").run(sender = bob.address, amount = sp.mutez(7500))
    scenario += test_match.place_bet("France").run(sender = alice.address, amount = sp.mutez(5000))
    scenario += test_match.place_bet("France").run(sender = p_a.address, amount = sp.mutez(10))
    scenario += test_match.remove_bet().run(sender = bob.address)
    scenario.verify(test_match.data.betted_amount["France"] == sp.mutez(5010))
    scenario += test_match.place_bet("Italie").run(sender = bob.address, amount = sp.mutez(23))
    scenario += test_match.place_bet("tie").run(sender = garfield.address, amount = sp.mutez(784))

    # Sending XTZ tests
    scenario += test_match.redeem_tez().run(sender = alice.address)

class Deployer(sp.Contract):
    def __init__(self):
        self.match = Match(sp.record(team_a = "Team A", team_b = "Team B"))
        self.init(x = sp.none)
        
    @sp.entry_point
    def deployContract(self, teams):
        self.data.x = sp.some(sp.create_contract(
        storage = sp.record(
        status = "Not started", 
        outcome = "NA", 
        total_betted_amount = sp.tez(0), 
        names = sp.map({"team_a": teams.team_a, "team_b": teams.team_b}),
        betted_amount = sp.map({teams.team_a: sp.tez(0), teams.team_b: sp.tez(0), "tie": sp.tez(0)}),
        rating = sp.map({teams.team_a: sp.pair(sp.nat(1), sp.tez(0)),teams.team_b: sp.pair(sp.nat(1), sp.tez(0)),"tie": sp.pair(sp.nat(1), sp.tez(0))})
        tx = sp.map({l = {}, tkey = sp.TAddress, tvalue = sp.TRecord(amount = sp.TMutez, choice = sp.TString)})
        ), 
        contract = self.match))
        self.data.x = sp.none
    
@sp.add_test(name = "Test")

def test():
    
    obj = Deployer()
    scenario = sp.test_scenario()
    scenario += obj
    scenario += obj.deployContract(sp.record(team_a = "Team A", team_b = "Team B"))