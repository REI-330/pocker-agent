"use strict";
const { RuleModule } = require("./runtime.cjs");
const PACKAGE = {
  "format": "card-game-core",
  "formatVersion": "0.28.0",
  "gameId": "high-card-race",
  "rulesetVersion": "0.3.0",
  "players": {
    "min": 2,
    "max": 6
  },
  "catalog": {
    "card": {
      "kind": "builtin",
      "preset": "poker-54",
      "options": {
        "jokers": "none"
      }
    },
    "group": {}
  },
  "cardZones": {
    "pool": {
      "name": "初始化牌池",
      "visibility": "none"
    },
    "deck": {
      "name": "牌堆",
      "visibility": "none"
    },
    "hands": {
      "name": "手牌",
      "visibility": "owner"
    },
    "discard": {
      "name": "弃牌堆",
      "visibility": "all"
    }
  },
  "initialState": {
    "phase": "setup",
    "round": 0,
    "pendingPlayers": {
      "$players": true
    },
    "scores": {
      "$perPlayer": 0
    }
  },
  "presentation": {
    "playerStats": [
      {
        "path": "scores",
        "label": "得分"
      }
    ],
    "actions": {
      "draw_card": {
        "nameKey": "action.drawCard",
        "descriptionKey": "action.drawCard.description",
        "iconKey": "draw-card"
      },
      "resolve_round": {
        "nameKey": "action.resolveRound",
        "iconKey": "resolve-round"
      }
    },
    "events": {
      "cards_drawn": {
        "animationKey": "deal-card",
        "soundKey": "card-deal"
      },
      "value_added": {
        "animationKey": "score-up",
        "soundKey": "score-point"
      },
      "items_moved": {
        "animationKey": "collect-cards",
        "soundKey": "cards-move"
      },
      "game_finished": {
        "animationKey": "game-result",
        "soundKey": "game-finished"
      }
    }
  },
  "functions": {
    "highest_rank_players": {
      "returns": "player_id[]",
      "body": {
        "$argmax": {
          "items": {
            "$path": "players"
          },
          "as": "_player",
          "by": {
            "@card_rank": {
              "@first": {
                "$zone": [
                  "hands",
                  {
                    "$var": "_player"
                  }
                ]
              }
            }
          }
        }
      }
    },
    "highest_score_players": {
      "returns": "player_id[]",
      "body": {
        "$argmax": {
          "items": {
            "$path": "players"
          },
          "as": "_player",
          "by": {
            "$path": [
              "scores",
              {
                "$var": "_player"
              }
            ]
          }
        }
      }
    }
  },
  "actions": [
    {
      "type": "shuffle_deck",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "setup"
        ]
      },
      "effects": [
        {
          "op": "$shuffle",
          "zone": "pool"
        },
        {
          "op": "$move_all",
          "source": {
            "zone": "pool"
          },
          "target": {
            "zone": "deck"
          }
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "drawing"
        }
      ]
    },
    {
      "type": "draw_card",
      "actor": "player",
      "args": [
        {
          "name": "count",
          "type": "integer",
          "required": true,
          "values": [
            1
          ]
        }
      ],
      "when": {
        "$and": [
          {
            "@eq": [
              {
                "$path": "phase"
              },
              "drawing"
            ]
          },
          {
            "@eq": [
              {
                "@first": {
                  "$path": "pendingPlayers"
                }
              },
              {
                "$var": "_actor"
              }
            ]
          }
        ]
      },
      "effects": [
        {
          "op": "$draw",
          "source": {
            "zone": "deck"
          },
          "target": {
            "zone": [
              "hands",
              {
                "$var": "_actor"
              }
            ]
          },
          "count": {
            "$arg": "count"
          }
        },
        {
          "op": "$remove",
          "path": "pendingPlayers",
          "value": {
            "$var": "_actor"
          }
        },
        {
          "op": "$if",
          "when": {
            "@is_empty": {
              "$path": "pendingPlayers"
            }
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "resolving"
            }
          ]
        }
      ]
    },
    {
      "type": "resolve_round",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "resolving"
        ]
      },
      "effects": [
        {
          "op": "$for_each_player",
          "effects": [
            {
              "op": "$reveal",
              "source": {
                "zone": [
                  "hands",
                  {
                    "$var": "_player"
                  }
                ]
              }
            }
          ]
        },
        {
          "op": "$for_each",
          "items": {
            "$call": "highest_rank_players"
          },
          "as": "_winner",
          "effects": [
            {
              "op": "$add",
              "path": [
                "scores",
                {
                  "$var": "_winner"
                }
              ],
              "value": 1
            }
          ]
        },
        {
          "op": "$add",
          "path": "round",
          "value": 1
        },
        {
          "op": "$for_each_player",
          "effects": [
            {
              "op": "$move_all",
              "source": {
                "zone": [
                  "hands",
                  {
                    "$var": "_player"
                  }
                ]
              },
              "target": {
                "zone": "discard"
              }
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "@gte": [
              {
                "@length": {
                  "$zone": "deck"
                }
              },
              {
                "@length": {
                  "$path": "players"
                }
              }
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "pendingPlayers",
              "value": {
                "$path": "players"
              }
            },
            {
              "op": "$set",
              "path": "phase",
              "value": "drawing"
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "@lt": [
              {
                "@length": {
                  "$zone": "deck"
                }
              },
              {
                "@length": {
                  "$path": "players"
                }
              }
            ]
          },
          "effects": [
            {
              "op": "$finish",
              "winner": {
                "$call": "highest_score_players"
              }
            }
          ]
        }
      ]
    }
  ]
};
const RULE_MODULE = new RuleModule(PACKAGE);
module.exports = {
  metadata: () => RULE_MODULE.metadata(),
  createGame: (players) => RULE_MODULE.createGame(players),
  getCatalog: (key) => RULE_MODULE.getCatalog(key),
  actionSchemas: () => RULE_MODULE.actionSchemas(),
  legalActions: (state, actor) => RULE_MODULE.legalActions(state, actor),
  activeActors: (state) => RULE_MODULE.activeActors(state),
  nodeKind: (state) => RULE_MODULE.nodeKind(state),
  chanceOutcomes: (state) => RULE_MODULE.chanceOutcomes(state),
  validateAction: (state, action) => RULE_MODULE.validateAction(state, action),
  applyAction: (state, action) => RULE_MODULE.applyAction(state, action),
  successors: (state, actor) => RULE_MODULE.successors(state, actor),
  observation: (state, viewer) => RULE_MODULE.observation(state, viewer),
  isFinished: (state) => RULE_MODULE.isFinished(state),
  result: (state) => RULE_MODULE.result(state),
  reduce: (state, events) => RULE_MODULE.reduce(state, events)
};
