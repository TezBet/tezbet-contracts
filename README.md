# :heart_on_fire: :soccer: TezBet :soccer: :heart_on_fire:

TezBet is a proposal for the Gitcoin's GameOn! hackathon. This project is the outcome of a four-people team, comprised of two smart contract devs and two frontend devs. We are very grateful to our two advisors for their suggestions and support all along the project.

## A decentralized approach to soccer betting 

:soccer: TezBet is a decentralized application built on the Tezos blockchain. Its philosophy is to be fully self-sufficient, resulting in a both decentralized and automated alternative to the average centralized soccer betting applications. 

:moneybag: TezBet's principle relies on the zero-sum game theory, which means that the bet winners share the total bet amount. Using this mechanism, TezBet does not need to store any backing liquidity to pay the winners.

:heavy_division_sign: Potential gains are thus calculated upon the total bet amount on each possible outcome. We do not rely on any odds calculated by a third party entity. 

## Roadmap

This an exhaustive list of the functionalities that we wanted to implement in TezBet. Most of them have already been developed but there is still a lot of work ahead of us to make it fully operational. For the time being, we cannot fetch the matches data in a decentralized manner; the displayed matches are sheer data fixtures.

### Smart contract
:heavy_check_mark: Creating a contract factory managing the matches

:heavy_check_mark: Placing bets on different matches and potential outcomes

:heavy_check_mark: Removing bets on different matches and potential outcomes

:heavy_check_mark: Computing the odds aka the potential gains

:heavy_check_mark: Updating the match status

:heavy_check_mark: Redeeming the gains of a won bet

:heavy_check_mark: Erasing a match from the database when all gains have been redeemed

:x: Using Chainlink to fetch the games and their outcome