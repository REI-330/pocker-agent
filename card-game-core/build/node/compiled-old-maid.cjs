"use strict";
const { RuleModule } = require("./runtime.cjs");
const PACKAGE = {
  "format": "card-game-core",
  "formatVersion": "0.28.0",
  "gameId": "old-maid-single-ghost",
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
        "jokers": "one-pair"
      },
      "copies": 1,
      "excludes": [
        {
          "id": "BJ",
          "copies": 1
        }
      ]
    },
    "group": {}
  },
  "cardZones": {
    "pool": {
      "name": "初始化牌池",
      "visibility": "none"
    },
    "deck": {
      "name": "发牌堆",
      "visibility": "none"
    },
    "hands": {
      "name": "手牌",
      "visibility": "owner"
    },
    "discard": {
      "name": "已配对的弃牌",
      "visibility": "all"
    }
  },
  "initialState": {
    "phase": "setup",
    "round": 0,
    "pendingPlayers": {
      "$players": true
    }
  },
  "functions": {
    "players_with_cards": {
      "returns": "player_id[]",
      "body": {
        "$filter": {
          "items": {
            "$path": "players"
          },
          "as": "_player",
          "where": {
            "@gt": [
              {
                "@length": {
                  "$zone": [
                    "hands",
                    {
                      "$var": "_player"
                    }
                  ]
                }
              },
              0
            ]
          }
        }
      }
    },
    "players_without_cards": {
      "returns": "player_id[]",
      "body": {
        "$filter": {
          "items": {
            "$path": "players"
          },
          "as": "_player",
          "where": {
            "@is_empty": {
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
    },
    "draw_source_players": {
      "returns": "player_id[]",
      "body": {
        "$if": {
          "when": {
            "$and": [
              {
                "@gte": [
                  {
                    "@length": {
                      "$call": "players_with_cards"
                    }
                  },
                  2
                ]
              },
              {
                "@contains": [
                  {
                    "$call": "players_with_cards"
                  },
                  {
                    "$var": "_actor"
                  }
                ]
              }
            ]
          },
          "then": [
            {
              "@at": [
                {
                  "$call": "players_with_cards"
                },
                {
                  "@mod": [
                    {
                      "@add": [
                        {
                          "@index_of": [
                            {
                              "$call": "players_with_cards"
                            },
                            {
                              "$var": "_actor"
                            }
                          ]
                        },
                        1
                      ]
                    },
                    {
                      "@length": {
                        "$call": "players_with_cards"
                      }
                    }
                  ]
                }
              ]
            }
          ],
          "else": []
        }
      }
    }
  },
  "actions": [
    {
      "type": "prepare_deck",
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
          "value": "dealing"
        }
      ]
    },
    {
      "type": "deal_pass",
      "actor": "system",
      "args": [],
      "when": {
        "$and": [
          {
            "@eq": [
              {
                "$path": "phase"
              },
              "dealing"
            ]
          },
          {
            "@gt": [
              {
                "@length": {
                  "$zone": "deck"
                }
              },
              0
            ]
          }
        ]
      },
      "effects": [
        {
          "op": "$for_each_player",
          "effects": [
            {
              "op": "$if",
              "when": {
                "@gt": [
                  {
                    "@length": {
                      "$zone": "deck"
                    }
                  },
                  0
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
                        "$var": "_player"
                      }
                    ]
                  },
                  "count": 1,
                  "from": "tail"
                }
              ]
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "@is_empty": {
              "$zone": "deck"
            }
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "initial_pairing"
            }
          ]
        }
      ]
    },
    {
      "type": "discard_pairs",
      "actor": "system",
      "args": [],
      "when": {
        "$or": [
          {
            "@eq": [
              {
                "$path": "phase"
              },
              "initial_pairing"
            ]
          },
          {
            "$and": [
              {
                "@eq": [
                  {
                    "$path": "phase"
                  },
                  "pairing"
                ]
              },
              {
                "$not": {
                  "@is_empty": {
                    "$path": "pendingPlayers"
                  }
                }
              }
            ]
          }
        ]
      },
      "effects": [
        {
          "op": "$for_each",
          "items": {
            "$if": {
              "when": {
                "@eq": [
                  {
                    "$path": "phase"
                  },
                  "initial_pairing"
                ]
              },
              "then": {
                "$path": "players"
              },
              "else": [
                {
                  "@first": {
                    "$path": "pendingPlayers"
                  }
                }
              ]
            }
          },
          "as": "_player",
          "effects": [
            {
              "op": "$for_each",
              "items": {
                "$group_by": {
                  "items": {
                    "$filter": {
                      "items": {
                        "$zone": [
                          "hands",
                          {
                            "$var": "_player"
                          }
                        ]
                      },
                      "as": "_card",
                      "where": {
                        "@ne": [
                          {
                            "$var": "_card"
                          },
                          "RJ"
                        ]
                      }
                    }
                  },
                  "as": "_card",
                  "by": {
                    "@card_rank": {
                      "$var": "_card"
                    }
                  }
                }
              },
              "as": "_pairGroup",
              "effects": [
                {
                  "op": "$if",
                  "when": {
                    "@gte": [
                      {
                        "@length": {
                          "@get": [
                            {
                              "$var": "_pairGroup"
                            },
                            "items"
                          ]
                        }
                      },
                      2
                    ]
                  },
                  "effects": [
                    {
                      "op": "$move_cards",
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
                      },
                      "cards": {
                        "$if": {
                          "when": {
                            "@eq": [
                              {
                                "@length": {
                                  "@get": [
                                    {
                                      "$var": "_pairGroup"
                                    },
                                    "items"
                                  ]
                                }
                              },
                              3
                            ]
                          },
                          "then": {
                            "@slice": [
                              {
                                "@get": [
                                  {
                                    "$var": "_pairGroup"
                                  },
                                  "items"
                                ]
                              },
                              0,
                              2
                            ]
                          },
                          "else": {
                            "@get": [
                              {
                                "$var": "_pairGroup"
                              },
                              "items"
                            ]
                          }
                        }
                      }
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "@eq": [
              {
                "$path": "phase"
              },
              "pairing"
            ]
          },
          "effects": [
            {
              "op": "$remove",
              "path": "pendingPlayers",
              "value": {
                "@first": {
                  "$path": "pendingPlayers"
                }
              }
            }
          ]
        },
        {
          "op": "$set",
          "path": "pendingPlayers",
          "value": {
            "$filter": {
              "items": {
                "$path": "pendingPlayers"
              },
              "as": "_player",
              "where": {
                "@contains": [
                  {
                    "$call": "players_with_cards"
                  },
                  {
                    "$var": "_player"
                  }
                ]
              }
            }
          }
        },
        {
          "op": "$if",
          "when": {
            "@gte": [
              {
                "@length": {
                  "$call": "players_with_cards"
                }
              },
              2
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "drawing"
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
                  "path": "pendingPlayers",
                  "value": {
                    "$call": "players_with_cards"
                  }
                },
                {
                  "op": "$add",
                  "path": "round",
                  "value": 1
                }
              ]
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "@eq": [
              {
                "@length": {
                  "$call": "players_with_cards"
                }
              },
              1
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "pendingPlayers",
              "value": []
            },
            {
              "op": "$finish",
              "winner": {
                "$call": "players_without_cards"
              }
            }
          ]
        }
      ]
    },
    {
      "type": "draw_card",
      "actor": "player",
      "args": [],
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
            "@gte": [
              {
                "@length": {
                  "$call": "players_with_cards"
                }
              },
              2
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
          },
          {
            "@contains": [
              {
                "$call": "players_with_cards"
              },
              {
                "$var": "_actor"
              }
            ]
          },
          {
            "@eq": [
              {
                "@length": {
                  "$call": "draw_source_players"
                }
              },
              1
            ]
          },
          {
            "@ne": [
              {
                "@first": {
                  "$call": "draw_source_players"
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
          "op": "$for_each",
          "items": {
            "$call": "draw_source_players"
          },
          "as": "_sourcePlayer",
          "effects": [
            {
              "op": "$draw",
              "source": {
                "zone": [
                  "hands",
                  {
                    "$var": "_sourcePlayer"
                  }
                ]
              },
              "target": {
                "zone": [
                  "hands",
                  {
                    "$var": "_actor"
                  }
                ]
              },
              "count": 1,
              "from": "random"
            }
          ]
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "pairing"
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
