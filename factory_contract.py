import smartpy as sp
​
class IncDec(sp.Contract):
    
    def __init__(self):
        self.init_type(sp.TRecord(counter = sp.TInt))
        
    @sp.entry_point
    def increment(self,params):
        self.data.counter += params.by
        
    @sp.entry_point
    def decrement(self,params):
        self.data.counter -= params.by
        
​
class Deployer(sp.Contract):
​
    def __init__(self):
        self.incDec = IncDec()
        self.init(x = sp.none)
        
    @sp.entry_point
    def deployContract(self,params):
        self.data.x = sp.some(sp.create_contract(storage = sp.record(counter = sp.int(0)), contract = self.incDec))
        self.data.x = sp.none
    
@sp.add_test(name = "Test")
​
def test():
    
    obj = Deployer()
    scenario = sp.test_scenario()
    scenario += obj
    scenario += obj.deployContract()