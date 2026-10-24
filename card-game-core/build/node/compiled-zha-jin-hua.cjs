"use strict";
const { RuleModule } = require("./runtime.cjs");
const PACKAGE = {
  "format": "card-game-core",
  "formatVersion": "0.28.0",
  "gameId": "zha-jin-hua",
  "rulesetVersion": "0.1.0",
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
    },
    "table": {
      "name": "比牌区",
      "visibility": "all"
    }
  },
  "presentation": {
    "playerStats": [
      {
        "path": "balances",
        "label": "余额"
      },
      {
        "path": "bets",
        "label": "下注"
      }
    ]
  },
  "initialState": {
    "phase": "setup",
    "round": 0,
    "pendingPlayers": {
      "$players": true
    },
    "scores": {
      "$perPlayer": 0
    },
    "balances": {
      "$perPlayer": 100
    },
    "bets": {
      "$perPlayer": 0
    },
    "activePlayers": {
      "$players": true
    },
    "winners": [],
    "pot": 0
  },
  "functions": {
    "hand_rank": {
      "returns": "rank_vector",
      "body": {
        "$let": {
          "bindings": [
            {
              "name": "_cards",
              "value": {
                "$zone": [
                  "hands",
                  {
                    "$var": "_player"
                  }
                ]
              }
            },
            {
              "name": "_ranks",
              "value": {
                "$map": {
                  "items": {
                    "$var": "_cards"
                  },
                  "as": "_card",
                  "by": {
                    "@card_rank": {
                      "$var": "_card"
                    }
                  }
                }
              }
            },
            {
              "name": "_suitGroups",
              "value": {
                "$group_by": {
                  "items": {
                    "$var": "_cards"
                  },
                  "as": "_card",
                  "by": {
                    "@card_attribute": {
                      "card": {
                        "$var": "_card"
                      },
                      "key": "suit"
                    }
                  }
                }
              }
            },
            {
              "name": "_rankGroups",
              "value": {
                "$group_by": {
                  "items": {
                    "$var": "_ranks"
                  },
                  "as": "_rank",
                  "by": {
                    "$var": "_rank"
                  }
                }
              }
            },
            {
              "name": "_sortedRanks",
              "value": {
                "$sort": {
                  "items": {
                    "$var": "_ranks"
                  },
                  "as": "_rank",
                  "by": {
                    "$var": "_rank"
                  },
                  "order": "desc"
                }
              }
            },
            {
              "name": "_pairGroups",
              "value": {
                "$filter": {
                  "items": {
                    "$var": "_rankGroups"
                  },
                  "as": "_group",
                  "where": {
                    "@eq": [
                      {
                        "@length": {
                          "@get": [
                            {
                              "$var": "_group"
                            },
                            "items"
                          ]
                        }
                      },
                      2
                    ]
                  }
                }
              }
            },
            {
              "name": "_pairRank",
              "value": {
                "$if": {
                  "when": {
                    "@gt": [
                      {
                        "@length": {
                          "$var": "_pairGroups"
                        }
                      },
                      0
                    ]
                  },
                  "then": {
                    "@get": [
                      {
                        "@first": {
                          "$var": "_pairGroups"
                        }
                      },
                      "key"
                    ]
                  },
                  "else": 0
                }
              }
            },
            {
              "name": "_kickerRanks",
              "value": {
                "$sort": {
                  "items": {
                    "$filter": {
                      "items": {
                        "$var": "_ranks"
                      },
                      "as": "_rank",
                      "where": {
                        "@ne": [
                          {
                            "$var": "_rank"
                          },
                          {
                            "$var": "_pairRank"
                          }
                        ]
                      }
                    }
                  },
                  "as": "_rank",
                  "by": {
                    "$var": "_rank"
                  },
                  "order": "desc"
                }
              }
            },
            {
              "name": "_lowStraight",
              "value": {
                "$and": [
                  {
                    "@eq": [
                      {
                        "@length": {
                          "@unique": {
                            "$var": "_ranks"
                          }
                        }
                      },
                      3
                    ]
                  },
                  {
                    "@contains": [
                      {
                        "$var": "_ranks"
                      },
                      14
                    ]
                  },
                  {
                    "@contains": [
                      {
                        "$var": "_ranks"
                      },
                      2
                    ]
                  },
                  {
                    "@contains": [
                      {
                        "$var": "_ranks"
                      },
                      3
                    ]
                  }
                ]
              }
            },
            {
              "name": "_pairCount",
              "value": {
                "$count": {
                  "items": {
                    "$var": "_rankGroups"
                  },
                  "as": "_group",
                  "where": {
                    "@eq": [
                      {
                        "@length": {
                          "@get": [
                            {
                              "$var": "_group"
                            },
                            "items"
                          ]
                        }
                      },
                      2
                    ]
                  }
                }
              }
            },
            {
              "name": "_tripleCount",
              "value": {
                "$count": {
                  "items": {
                    "$var": "_rankGroups"
                  },
                  "as": "_group",
                  "where": {
                    "@eq": [
                      {
                        "@length": {
                          "@get": [
                            {
                              "$var": "_group"
                            },
                            "items"
                          ]
                        }
                      },
                      3
                    ]
                  }
                }
              }
            },
            {
              "name": "_flush",
              "value": {
                "@eq": [
                  {
                    "@length": {
                      "@get": [
                        {
                          "@first": {
                            "$var": "_suitGroups"
                          }
                        },
                        "items"
                      ]
                    }
                  },
                  3
                ]
              }
            },
            {
              "name": "_straight",
              "value": {
                "$or": [
                  {
                    "$and": [
                      {
                        "@eq": [
                          {
                            "@length": {
                              "@unique": {
                                "$var": "_ranks"
                              }
                            }
                          },
                          3
                        ]
                      },
                      {
                        "@eq": [
                          {
                            "@subtract": [
                              {
                                "@at": [
                                  {
                                    "$sort": {
                                      "items": {
                                        "$var": "_ranks"
                                      },
                                      "as": "_rank",
                                      "by": {
                                        "$var": "_rank"
                                      },
                                      "order": "desc"
                                    }
                                  },
                                  0
                                ]
                              },
                              {
                                "@at": [
                                  {
                                    "$sort": {
                                      "items": {
                                        "$var": "_ranks"
                                      },
                                      "as": "_rank",
                                      "by": {
                                        "$var": "_rank"
                                      },
                                      "order": "desc"
                                    }
                                  },
                                  2
                                ]
                              }
                            ]
                          },
                          2
                        ]
                      }
                    ]
                  },
                  {
                    "$var": "_lowStraight"
                  }
                ]
              }
            }
          ],
          "body": {
            "$if": {
              "when": {
                "@eq": [
                  {
                    "$var": "_tripleCount"
                  },
                  1
                ]
              },
              "then": {
                "$rank_vector": {
                  "category": [
                    6
                  ],
                  "tieBreakers": {
                    "$var": "_sortedRanks"
                  }
                }
              },
              "else": {
                "$if": {
                  "when": {
                    "$and": [
                      {
                        "$var": "_straight"
                      },
                      {
                        "$var": "_flush"
                      }
                    ]
                  },
                  "then": {
                    "$rank_vector": {
                      "category": [
                        5
                      ],
                      "tieBreakers": {
                        "$var": "_sortedRanks"
                      }
                    }
                  },
                  "else": {
                    "$if": {
                      "when": {
                        "$var": "_flush"
                      },
                      "then": {
                        "$rank_vector": {
                          "category": [
                            4
                          ],
                          "tieBreakers": {
                            "$var": "_sortedRanks"
                          }
                        }
                      },
                      "else": {
                        "$if": {
                          "when": {
                            "$var": "_straight"
                          },
                          "then": {
                            "$rank_vector": {
                              "category": [
                                3
                              ],
                              "tieBreakers": {
                                "$if": {
                                  "when": {
                                    "$var": "_lowStraight"
                                  },
                                  "then": [
                                    3,
                                    2,
                                    1
                                  ],
                                  "else": {
                                    "$var": "_sortedRanks"
                                  }
                                }
                              }
                            }
                          },
                          "else": {
                            "$if": {
                              "when": {
                                "@eq": [
                                  {
                                    "$var": "_pairCount"
                                  },
                                  1
                                ]
                              },
                              "then": {
                                "$rank_vector": {
                                  "category": [
                                    2
                                  ],
                                  "tieBreakers": [
                                    {
                                      "$var": "_pairRank"
                                    },
                                    {
                                      "@first": {
                                        "$var": "_kickerRanks"
                                      }
                                    }
                                  ]
                                }
                              },
                              "else": {
                                "$rank_vector": {
                                  "category": [
                                    1
                                  ],
                                  "tieBreakers": {
                                    "$var": "_sortedRanks"
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "winner": {
      "returns": "player_id[]",
      "body": {
        "$argmax": {
          "items": {
            "$path": "activePlayers"
          },
          "as": "_player",
          "by": {
            "$call": "hand_rank"
          }
        }
      }
    },
    "eligible_players": {
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
                "$path": [
                  "balances",
                  {
                    "$var": "_player"
                  }
                ]
              },
              0
            ]
          }
        }
      }
    },
    "next_round_players": {
      "returns": "player_id[]",
      "body": {
        "$let": {
          "bindings": [
            {
              "name": "_eligible",
              "value": {
                "$call": "eligible_players"
              }
            },
            {
              "name": "_winnerIndex",
              "value": {
                "@index_of": [
                  {
                    "$var": "_eligible"
                  },
                  {
                    "@first": {
                      "$path": "winners"
                    }
                  }
                ]
              }
            }
          ],
          "body": {
            "$if": {
              "when": {
                "$and": [
                  {
                    "@gt": [
                      {
                        "@length": {
                          "$path": "winners"
                        }
                      },
                      0
                    ]
                  },
                  {
                    "@gte": [
                      {
                        "$var": "_winnerIndex"
                      },
                      0
                    ]
                  }
                ]
              },
              "then": {
                "@concat": [
                  {
                    "@slice": [
                      {
                        "$var": "_eligible"
                      },
                      {
                        "@add": [
                          {
                            "$var": "_winnerIndex"
                          },
                          1
                        ]
                      },
                      {
                        "@length": {
                          "$var": "_eligible"
                        }
                      }
                    ]
                  },
                  {
                    "@slice": [
                      {
                        "$var": "_eligible"
                      },
                      0,
                      {
                        "@add": [
                          {
                            "$var": "_winnerIndex"
                          },
                          1
                        ]
                      }
                    ]
                  }
                ]
              },
              "else": {
                "$var": "_eligible"
              }
            }
          }
        }
      }
    },
    "matched_bet": {
      "returns": "number",
      "body": {
        "@get": [
          {
            "$path": "bets"
          },
          {
            "@first": {
              "$sort": {
                "items": {
                  "$path": "activePlayers"
                },
                "as": "_player",
                "by": {
                  "$path": [
                    "bets",
                    {
                      "$var": "_player"
                    }
                  ]
                },
                "order": "asc"
              }
            }
          }
        ]
      }
    },
    "highest_bet": {
      "returns": "number",
      "body": {
        "@get": [
          {
            "$path": "bets"
          },
          {
            "@first": {
              "$argmax": {
                "items": {
                  "$path": "activePlayers"
                },
                "as": "_player",
                "by": {
                  "$path": [
                    "bets",
                    {
                      "$var": "_player"
                    }
                  ]
                }
              }
            }
          }
        ]
      }
    },
    "refund_total": {
      "returns": "number",
      "body": {
        "$sum": {
          "items": {
            "$path": "activePlayers"
          },
          "as": "_player",
          "by": {
            "@subtract": [
              {
                "$path": [
                  "bets",
                  {
                    "$var": "_player"
                  }
                ]
              },
              {
                "$call": "matched_bet"
              }
            ]
          }
        }
      }
    },
    "players_to_call": {
      "returns": "player_id[]",
      "body": {
        "$filter": {
          "items": {
            "$path": "activePlayers"
          },
          "as": "_player",
          "where": {
            "$and": [
              {
                "@gt": [
                  {
                    "$path": [
                      "balances",
                      {
                        "$var": "_player"
                      }
                    ]
                  },
                  0
                ]
              },
              {
                "@lt": [
                  {
                    "$path": [
                      "bets",
                      {
                        "$var": "_player"
                      }
                    ]
                  },
                  {
                    "@get": [
                      {
                        "$path": "bets"
                      },
                      {
                        "@first": {
                          "$argmax": {
                            "items": {
                              "$path": "activePlayers"
                            },
                            "as": "_leader",
                            "by": {
                              "$path": [
                                "bets",
                                {
                                  "$var": "_leader"
                                }
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
          }
        }
      }
    }
  },
  "actions": [
    {
      "type": "start_round",
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
          "op": "$move_all",
          "source": {
            "zone": "discard"
          },
          "target": {
            "zone": "pool"
          }
        },
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
          "path": "activePlayers",
          "value": {
            "$call": "next_round_players"
          }
        },
        {
          "op": "$set",
          "path": "pendingPlayers",
          "value": {
            "$call": "next_round_players"
          }
        },
        {
          "op": "$for_each_player",
          "effects": [
            {
              "op": "$if",
              "when": {
                "@contains": [
                  {
                    "$path": "activePlayers"
                  },
                  {
                    "$var": "_player"
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
                        "$var": "_player"
                      }
                    ]
                  },
                  "count": 3
                }
              ]
            }
          ]
        },
        {
          "op": "$set",
          "path": "pot",
          "value": 0
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "betting"
        },
        {
          "op": "$add",
          "path": "round",
          "value": 1
        }
      ]
    },
    {
      "type": "bet",
      "actor": "player",
      "args": [
        {
          "name": "amount",
          "type": "number",
          "required": true,
          "min": {
            "$if": {
              "when": {
                "@gt": [
                  {
                    "$call": "highest_bet"
                  },
                  {
                    "$path": [
                      "bets",
                      {
                        "$var": "_actor"
                      }
                    ]
                  }
                ]
              },
              "then": {
                "$if": {
                  "when": {
                    "@lt": [
                      {
                        "$path": [
                          "balances",
                          {
                            "$var": "_actor"
                          }
                        ]
                      },
                      {
                        "@subtract": [
                          {
                            "$call": "highest_bet"
                          },
                          {
                            "$path": [
                              "bets",
                              {
                                "$var": "_actor"
                              }
                            ]
                          }
                        ]
                      }
                    ]
                  },
                  "then": {
                    "$path": [
                      "balances",
                      {
                        "$var": "_actor"
                      }
                    ]
                  },
                  "else": {
                    "@subtract": [
                      {
                        "$call": "highest_bet"
                      },
                      {
                        "$path": [
                          "bets",
                          {
                            "$var": "_actor"
                          }
                        ]
                      }
                    ]
                  }
                }
              },
              "else": 1
            }
          },
          "max": 100
        }
      ],
      "when": {
        "$and": [
          {
            "@eq": [
              {
                "$path": "phase"
              },
              "betting"
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
                "$path": "activePlayers"
              },
              {
                "$var": "_actor"
              }
            ]
          },
          {
            "@gte": [
              {
                "$path": [
                  "balances",
                  {
                    "$var": "_actor"
                  }
                ]
              },
              {
                "$arg": "amount"
              }
            ]
          }
        ]
      },
      "effects": [
        {
          "op": "$add",
          "path": [
            "balances",
            {
              "$var": "_actor"
            }
          ],
          "value": {
            "@subtract": [
              0,
              {
                "$arg": "amount"
              }
            ]
          }
        },
        {
          "op": "$add",
          "path": [
            "bets",
            {
              "$var": "_actor"
            }
          ],
          "value": {
            "$arg": "amount"
          }
        },
        {
          "op": "$add",
          "path": "pot",
          "value": {
            "$arg": "amount"
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
            "@eq": [
              {
                "@length": {
                  "$path": "activePlayers"
                }
              },
              1
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "showdown"
            }
          ]
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
              "op": "$if",
              "when": {
                "@is_empty": {
                  "$call": "players_to_call"
                }
              },
              "effects": [
                {
                  "op": "$set",
                  "path": "phase",
                  "value": "showdown"
                }
              ]
            },
            {
              "op": "$if",
              "when": {
                "$not": {
                  "@is_empty": {
                    "$call": "players_to_call"
                  }
                }
              },
              "effects": [
                {
                  "op": "$set",
                  "path": "pendingPlayers",
                  "value": {
                    "$call": "players_to_call"
                  }
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "fold",
      "actor": "player",
      "args": [],
      "when": {
        "$and": [
          {
            "@eq": [
              {
                "$path": "phase"
              },
              "betting"
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
                "$path": "activePlayers"
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
          "op": "$remove",
          "path": "pendingPlayers",
          "value": {
            "$var": "_actor"
          }
        },
        {
          "op": "$remove",
          "path": "activePlayers",
          "value": {
            "$var": "_actor"
          }
        },
        {
          "op": "$if",
          "when": {
            "@eq": [
              {
                "@length": {
                  "$path": "activePlayers"
                }
              },
              1
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "showdown"
            }
          ]
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
              "value": "showdown"
            }
          ]
        }
      ]
    },
    {
      "type": "showdown",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "showdown"
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
          "op": "$for_each_player",
          "effects": [
            {
              "op": "$if",
              "when": {
                "@gt": [
                  {
                    "$path": [
                      "bets",
                      {
                        "$var": "_player"
                      }
                    ]
                  },
                  {
                    "$call": "matched_bet"
                  }
                ]
              },
              "effects": [
                {
                  "op": "$add",
                  "path": [
                    "balances",
                    {
                      "$var": "_player"
                    }
                  ],
                  "value": {
                    "@subtract": [
                      {
                        "$path": [
                          "bets",
                          {
                            "$var": "_player"
                          }
                        ]
                      },
                      {
                        "$call": "matched_bet"
                      }
                    ]
                  }
                },
                {
                  "op": "$add",
                  "path": "pot",
                  "value": {
                    "@subtract": [
                      0,
                      {
                        "@subtract": [
                          {
                            "$path": [
                              "bets",
                              {
                                "$var": "_player"
                              }
                            ]
                          },
                          {
                            "$call": "matched_bet"
                          }
                        ]
                      }
                    ]
                  }
                }
              ]
            }
          ]
        },
        {
          "op": "$set",
          "path": "winners",
          "value": {
            "$call": "winner"
          }
        },
        {
          "op": "$for_each",
          "items": {
            "$call": "winner"
          },
          "as": "_winner",
          "effects": [
            {
              "op": "$add",
              "path": [
                "balances",
                {
                  "$var": "_winner"
                }
              ],
              "value": {
                "$path": "pot"
              }
            }
          ]
        },
        {
          "op": "$for_each_player",
          "effects": [
            {
              "op": "$set",
              "path": [
                "bets",
                {
                  "$var": "_player"
                }
              ],
              "value": 0
            },
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
          "op": "$set",
          "path": "pot",
          "value": 0
        },
        {
          "op": "$if",
          "when": {
            "@lte": [
              {
                "@length": {
                  "$call": "eligible_players"
                }
              },
              1
            ]
          },
          "effects": [
            {
              "op": "$finish",
              "winner": {
                "$call": "eligible_players"
              }
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "@gt": [
              {
                "@length": {
                  "$call": "eligible_players"
                }
              },
              1
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "setup"
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
