"use strict";
const { RuleModule } = require("./runtime.cjs");
const PACKAGE = {
  "format": "card-game-core",
  "formatVersion": "0.28.0",
  "gameId": "guandan-level-match",
  "rulesetVersion": "0.2.0",
  "players": {
    "min": 4,
    "max": 4
  },
  "catalog": {
    "card": {
      "kind": "builtin",
      "preset": "poker-54",
      "copies": 2,
      "options": {
        "jokers": "one-pair",
        "aceTwo": "ace-high"
      }
    },
    "group": {}
  },
  "cardZones": {
    "pool": {
      "name": "初始化及回收牌池",
      "visibility": "none"
    },
    "deck": {
      "name": "牌堆",
      "visibility": "none"
    },
    "hands": {
      "name": "手牌",
      "visibility": "owner",
      "max": 28
    },
    "table": {
      "name": "当前出牌",
      "visibility": "all",
      "max": 108
    },
    "discard": {
      "name": "已出牌",
      "visibility": "all"
    },
    "tableau1": {
      "name": "待公开的贡牌或抗贡证明",
      "visibility": "owner",
      "max": 2
    },
    "tableau2": {
      "name": "待交换的还牌",
      "visibility": "owner",
      "max": 1
    }
  },
  "stateSchema": {
    "level": {
      "type": "integer",
      "visibility": "all",
      "minimum": 2,
      "maximum": 14
    },
    "turn": {
      "type": "player_id",
      "visibility": "all"
    },
    "lastPlayer": {
      "type": "player_id",
      "visibility": "all"
    },
    "lastKind": {
      "type": "integer",
      "visibility": "all",
      "minimum": 0,
      "maximum": 10
    },
    "lastPower": {
      "type": "integer",
      "visibility": "all",
      "minimum": 0,
      "maximum": 20
    },
    "lastStrength": {
      "type": "integer",
      "visibility": "all",
      "minimum": 0,
      "maximum": 17
    },
    "lastWildRank1": {
      "type": "integer",
      "visibility": "all",
      "minimum": 0,
      "maximum": 14
    },
    "lastWildRank2": {
      "type": "integer",
      "visibility": "all",
      "minimum": 0,
      "maximum": 14
    },
    "lastWildSuit1": {
      "type": "integer",
      "visibility": "all",
      "minimum": 0,
      "maximum": 4
    },
    "lastWildSuit2": {
      "type": "integer",
      "visibility": "all",
      "minimum": 0,
      "maximum": 4
    },
    "lastAceLow": {
      "type": "boolean",
      "visibility": "all"
    },
    "finishOrder": {
      "type": "player_id[]",
      "visibility": "all"
    },
    "previousOrder": {
      "type": "player_id[]",
      "visibility": "all"
    },
    "openingPlayer": {
      "type": "player_id",
      "visibility": "all"
    },
    "anchorCard": {
      "type": "string",
      "visibility": "all"
    },
    "tributeTo": {
      "type": "player_id",
      "visibility": "all",
      "perPlayer": true
    },
    "tributeFrom": {
      "type": "player_id",
      "visibility": "all",
      "perPlayer": true
    },
    "tributeFace": {
      "type": "string",
      "visibility": "all",
      "perPlayer": true
    },
    "antiTributeKingCount": {
      "type": "integer",
      "visibility": "all",
      "perPlayer": true,
      "minimum": 0,
      "maximum": 2
    }
  },
  "initialState": {
    "phase": "setup",
    "round": 0,
    "pendingPlayers": [],
    "scores": {
      "$perPlayer": 2
    },
    "variables": {
      "level": 2,
      "turn": {
        "$firstPlayer": true
      },
      "lastPlayer": {
        "$firstPlayer": true
      },
      "lastKind": 0,
      "lastPower": 0,
      "lastStrength": 0,
      "lastWildRank1": 0,
      "lastWildRank2": 0,
      "lastWildSuit1": 0,
      "lastWildSuit2": 0,
      "lastAceLow": false,
      "finishOrder": [],
      "previousOrder": [],
      "openingPlayer": {
        "$firstPlayer": true
      },
      "anchorCard": "",
      "tributeTo": {
        "$perPlayer": {
          "$firstPlayer": true
        }
      },
      "tributeFrom": {
        "$perPlayer": {
          "$firstPlayer": true
        }
      },
      "tributeFace": {
        "$perPlayer": ""
      },
      "antiTributeKingCount": {
        "$perPlayer": 0
      }
    }
  },
  "presentation": {
    "actions": {
      "play_cards": {
        "nameKey": "action.guandan.play_cards",
        "descriptionKey": "action.guandan.play_cards.description"
      },
      "pass": {
        "nameKey": "action.guandan.pass",
        "descriptionKey": "action.guandan.pass.description"
      },
      "give_tribute": {
        "nameKey": "action.guandan.give_tribute",
        "descriptionKey": "action.guandan.give_tribute.description"
      },
      "return_tribute": {
        "nameKey": "action.guandan.return_tribute",
        "descriptionKey": "action.guandan.return_tribute.description"
      }
    },
    "playerStats": [
      {
        "path": "scores",
        "label": "队伍级数"
      }
    ]
  },
  "functions": {
    "natural_rank": {
      "returns": "number",
      "body": {
        "$if": {
          "when": {
            "@contains": [
              [
                "RJ#1",
                "RJ#2"
              ],
              {
                "$var": "_card"
              }
            ]
          },
          "then": 17,
          "else": {
            "$if": {
              "when": {
                "@contains": [
                  [
                    "BJ#1",
                    "BJ#2"
                  ],
                  {
                    "$var": "_card"
                  }
                ]
              },
              "then": 16,
              "else": {
                "@card_rank": {
                  "$var": "_card"
                }
              }
            }
          }
        }
      }
    },
    "is_wild": {
      "returns": "number",
      "body": {
        "$if": {
          "when": {
            "$if": {
              "when": {
                "@contains": [
                  [
                    "BJ#1",
                    "BJ#2",
                    "RJ#1",
                    "RJ#2"
                  ],
                  {
                    "$var": "_card"
                  }
                ]
              },
              "then": false,
              "else": {
                "$and": [
                  {
                    "@eq": [
                      {
                        "@card_rank": {
                          "$var": "_card"
                        }
                      },
                      {
                        "$path": "variables.level"
                      }
                    ]
                  },
                  {
                    "@eq": [
                      {
                        "@card_attribute": {
                          "card": {
                            "$var": "_card"
                          },
                          "key": "suit"
                        }
                      },
                      "hearts"
                    ]
                  }
                ]
              }
            }
          },
          "then": 1,
          "else": 0
        }
      }
    },
    "rank_strength": {
      "returns": "number",
      "body": {
        "$if": {
          "when": {
            "@eq": [
              {
                "$var": "_rank"
              },
              {
                "$path": "variables.level"
              }
            ]
          },
          "then": 15,
          "else": {
            "$var": "_rank"
          }
        }
      }
    },
    "card_strength": {
      "returns": "number",
      "body": {
        "$let": {
          "bindings": [
            {
              "name": "_rank",
              "value": {
                "$call": "natural_rank"
              }
            }
          ],
          "body": {
            "$call": "rank_strength"
          }
        }
      }
    },
    "effective_rank": {
      "returns": "number",
      "body": {
        "$if": {
          "when": {
            "@eq": [
              {
                "$call": "is_wild"
              },
              1
            ]
          },
          "then": {
            "$if": {
              "when": {
                "@contains": [
                  [
                    "2H#1",
                    "3H#1",
                    "4H#1",
                    "5H#1",
                    "6H#1",
                    "7H#1",
                    "8H#1",
                    "9H#1",
                    "10H#1",
                    "JH#1",
                    "QH#1",
                    "KH#1",
                    "AH#1"
                  ],
                  {
                    "$var": "_card"
                  }
                ]
              },
              "then": {
                "$if": {
                  "when": {
                    "@eq": [
                      {
                        "$arg": "wildRank1"
                      },
                      0
                    ]
                  },
                  "then": {
                    "$call": "natural_rank"
                  },
                  "else": {
                    "$arg": "wildRank1"
                  }
                }
              },
              "else": {
                "$if": {
                  "when": {
                    "@eq": [
                      {
                        "$arg": "wildRank2"
                      },
                      0
                    ]
                  },
                  "then": {
                    "$call": "natural_rank"
                  },
                  "else": {
                    "$arg": "wildRank2"
                  }
                }
              }
            }
          },
          "else": {
            "$call": "natural_rank"
          }
        }
      }
    },
    "play_descriptor": {
      "returns": "rank_vector",
      "body": {
        "$let": {
          "bindings": [
            {
              "name": "_cards",
              "value": {
                "$filter": {
                  "items": [
                    {
                      "$arg": "card1"
                    },
                    {
                      "$arg": "card2"
                    },
                    {
                      "$arg": "card3"
                    },
                    {
                      "$arg": "card4"
                    },
                    {
                      "$arg": "card5"
                    },
                    {
                      "$arg": "card6"
                    },
                    {
                      "$arg": "card7"
                    },
                    {
                      "$arg": "card8"
                    },
                    {
                      "$arg": "card9"
                    },
                    {
                      "$arg": "card10"
                    }
                  ],
                  "as": "_selectedCard",
                  "where": {
                    "@ne": [
                      {
                        "$var": "_selectedCard"
                      },
                      ""
                    ]
                  }
                }
              }
            },
            {
              "name": "_n",
              "value": {
                "@length": {
                  "$var": "_cards"
                }
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
                    "$if": {
                      "when": {
                        "$and": [
                          {
                            "@contains": [
                              [
                                5,
                                6,
                                7,
                                9
                              ],
                              {
                                "$arg": "kind"
                              }
                            ]
                          },
                          {
                            "$arg": "aceLow"
                          },
                          {
                            "@eq": [
                              {
                                "$call": "effective_rank"
                              },
                              14
                            ]
                          }
                        ]
                      },
                      "then": 1,
                      "else": {
                        "$call": "effective_rank"
                      }
                    }
                  }
                }
              }
            },
            {
              "name": "_suits",
              "value": {
                "$map": {
                  "items": {
                    "$var": "_cards"
                  },
                  "as": "_card",
                  "by": {
                    "$if": {
                      "when": {
                        "@contains": [
                          [
                            "BJ#1",
                            "BJ#2",
                            "RJ#1",
                            "RJ#2"
                          ],
                          {
                            "$var": "_card"
                          }
                        ]
                      },
                      "then": "joker",
                      "else": {
                        "$if": {
                          "when": {
                            "$and": [
                              {
                                "@eq": [
                                  {
                                    "$call": "is_wild"
                                  },
                                  1
                                ]
                              },
                              {
                                "@ne": [
                                  {
                                    "$if": {
                                      "when": {
                                        "@contains": [
                                          [
                                            "2H#1",
                                            "3H#1",
                                            "4H#1",
                                            "5H#1",
                                            "6H#1",
                                            "7H#1",
                                            "8H#1",
                                            "9H#1",
                                            "10H#1",
                                            "JH#1",
                                            "QH#1",
                                            "KH#1",
                                            "AH#1"
                                          ],
                                          {
                                            "$var": "_card"
                                          }
                                        ]
                                      },
                                      "then": {
                                        "$arg": "wildSuit1"
                                      },
                                      "else": {
                                        "$arg": "wildSuit2"
                                      }
                                    }
                                  },
                                  0
                                ]
                              }
                            ]
                          },
                          "then": {
                            "@at": [
                              [
                                "hearts",
                                "diamonds",
                                "clubs",
                                "spades"
                              ],
                              {
                                "@subtract": [
                                  {
                                    "$if": {
                                      "when": {
                                        "@contains": [
                                          [
                                            "2H#1",
                                            "3H#1",
                                            "4H#1",
                                            "5H#1",
                                            "6H#1",
                                            "7H#1",
                                            "8H#1",
                                            "9H#1",
                                            "10H#1",
                                            "JH#1",
                                            "QH#1",
                                            "KH#1",
                                            "AH#1"
                                          ],
                                          {
                                            "$var": "_card"
                                          }
                                        ]
                                      },
                                      "then": {
                                        "$arg": "wildSuit1"
                                      },
                                      "else": {
                                        "$arg": "wildSuit2"
                                      }
                                    }
                                  },
                                  1
                                ]
                              }
                            ]
                          },
                          "else": {
                            "@card_attribute": {
                              "card": {
                                "$var": "_card"
                              },
                              "key": "suit"
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            },
            {
              "name": "_groups",
              "value": {
                "$group_by": {
                  "items": {
                    "$var": "_ranks"
                  },
                  "as": "_r",
                  "by": {
                    "$var": "_r"
                  }
                }
              }
            },
            {
              "name": "_ordered",
              "value": {
                "$sort": {
                  "items": {
                    "@unique": {
                      "$var": "_ranks"
                    }
                  },
                  "as": "_r",
                  "by": {
                    "$var": "_r"
                  },
                  "order": "asc"
                }
              }
            },
            {
              "name": "_base",
              "value": {
                "$if": {
                  "when": {
                    "@gt": [
                      {
                        "$var": "_n"
                      },
                      0
                    ]
                  },
                  "then": {
                    "@first": {
                      "$var": "_ordered"
                    }
                  },
                  "else": 0
                }
              }
            },
            {
              "name": "_top",
              "value": {
                "$if": {
                  "when": {
                    "@gt": [
                      {
                        "$var": "_n"
                      },
                      0
                    ]
                  },
                  "then": {
                    "@at": [
                      {
                        "$var": "_ordered"
                      },
                      {
                        "@subtract": [
                          {
                            "@length": {
                              "$var": "_ordered"
                            }
                          },
                          1
                        ]
                      }
                    ]
                  },
                  "else": 0
                }
              }
            },
            {
              "name": "_pairs",
              "value": {
                "$filter": {
                  "items": {
                    "$var": "_groups"
                  },
                  "as": "_g",
                  "where": {
                    "@eq": [
                      {
                        "@length": {
                          "@get": [
                            {
                              "$var": "_g"
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
              "name": "_triples",
              "value": {
                "$filter": {
                  "items": {
                    "$var": "_groups"
                  },
                  "as": "_g",
                  "where": {
                    "@eq": [
                      {
                        "@length": {
                          "@get": [
                            {
                              "$var": "_g"
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
              "name": "_consecutive",
              "value": {
                "$and": [
                  {
                    "@eq": [
                      {
                        "@subtract": [
                          {
                            "$var": "_top"
                          },
                          {
                            "$var": "_base"
                          }
                        ]
                      },
                      {
                        "@subtract": [
                          {
                            "@length": {
                              "$var": "_groups"
                            }
                          },
                          1
                        ]
                      }
                    ]
                  },
                  {
                    "@lte": [
                      {
                        "$var": "_top"
                      },
                      14
                    ]
                  }
                ]
              }
            },
            {
              "name": "_shapeValid",
              "value": {
                "$if": {
                  "when": {
                    "@eq": [
                      {
                        "$arg": "kind"
                      },
                      1
                    ]
                  },
                  "then": {
                    "$and": [
                      {
                        "@eq": [
                          {
                            "$var": "_n"
                          },
                          1
                        ]
                      },
                      {
                        "@eq": [
                          {
                            "$arg": "wildRank1"
                          },
                          0
                        ]
                      },
                      {
                        "@eq": [
                          {
                            "$arg": "wildRank2"
                          },
                          0
                        ]
                      },
                      {
                        "@eq": [
                          {
                            "$arg": "wildSuit1"
                          },
                          0
                        ]
                      },
                      {
                        "@eq": [
                          {
                            "$arg": "wildSuit2"
                          },
                          0
                        ]
                      }
                    ]
                  },
                  "else": {
                    "$if": {
                      "when": {
                        "@eq": [
                          {
                            "$arg": "kind"
                          },
                          2
                        ]
                      },
                      "then": {
                        "$and": [
                          {
                            "@eq": [
                              {
                                "$var": "_n"
                              },
                              2
                            ]
                          },
                          {
                            "@eq": [
                              {
                                "@length": {
                                  "$var": "_groups"
                                }
                              },
                              1
                            ]
                          }
                        ]
                      },
                      "else": {
                        "$if": {
                          "when": {
                            "@eq": [
                              {
                                "$arg": "kind"
                              },
                              3
                            ]
                          },
                          "then": {
                            "$and": [
                              {
                                "@eq": [
                                  {
                                    "$var": "_n"
                                  },
                                  3
                                ]
                              },
                              {
                                "@eq": [
                                  {
                                    "@length": {
                                      "$var": "_groups"
                                    }
                                  },
                                  1
                                ]
                              },
                              {
                                "@lte": [
                                  {
                                    "$var": "_base"
                                  },
                                  14
                                ]
                              }
                            ]
                          },
                          "else": {
                            "$if": {
                              "when": {
                                "@eq": [
                                  {
                                    "$arg": "kind"
                                  },
                                  4
                                ]
                              },
                              "then": {
                                "$and": [
                                  {
                                    "@eq": [
                                      {
                                        "$var": "_n"
                                      },
                                      5
                                    ]
                                  },
                                  {
                                    "@eq": [
                                      {
                                        "@length": {
                                          "$var": "_groups"
                                        }
                                      },
                                      2
                                    ]
                                  },
                                  {
                                    "@eq": [
                                      {
                                        "@length": {
                                          "$var": "_triples"
                                        }
                                      },
                                      1
                                    ]
                                  },
                                  {
                                    "@eq": [
                                      {
                                        "@length": {
                                          "$var": "_pairs"
                                        }
                                      },
                                      1
                                    ]
                                  },
                                  {
                                    "@lte": [
                                      {
                                        "$if": {
                                          "when": {
                                            "@gt": [
                                              {
                                                "@length": {
                                                  "$var": "_triples"
                                                }
                                              },
                                              0
                                            ]
                                          },
                                          "then": {
                                            "@get": [
                                              {
                                                "@first": {
                                                  "$var": "_triples"
                                                }
                                              },
                                              "key"
                                            ]
                                          },
                                          "else": 0
                                        }
                                      },
                                      14
                                    ]
                                  }
                                ]
                              },
                              "else": {
                                "$if": {
                                  "when": {
                                    "$or": [
                                      {
                                        "@eq": [
                                          {
                                            "$arg": "kind"
                                          },
                                          5
                                        ]
                                      },
                                      {
                                        "@eq": [
                                          {
                                            "$arg": "kind"
                                          },
                                          9
                                        ]
                                      }
                                    ]
                                  },
                                  "then": {
                                    "$and": [
                                      {
                                        "@eq": [
                                          {
                                            "$var": "_n"
                                          },
                                          5
                                        ]
                                      },
                                      {
                                        "@eq": [
                                          {
                                            "@length": {
                                              "$var": "_groups"
                                            }
                                          },
                                          5
                                        ]
                                      },
                                      {
                                        "$var": "_consecutive"
                                      },
                                      {
                                        "$if": {
                                          "when": {
                                            "@eq": [
                                              {
                                                "$arg": "kind"
                                              },
                                              9
                                            ]
                                          },
                                          "then": {
                                            "@eq": [
                                              {
                                                "@length": {
                                                  "@unique": {
                                                    "$var": "_suits"
                                                  }
                                                }
                                              },
                                              1
                                            ]
                                          },
                                          "else": true
                                        }
                                      }
                                    ]
                                  },
                                  "else": {
                                    "$if": {
                                      "when": {
                                        "@eq": [
                                          {
                                            "$arg": "kind"
                                          },
                                          6
                                        ]
                                      },
                                      "then": {
                                        "$and": [
                                          {
                                            "@eq": [
                                              {
                                                "$var": "_n"
                                              },
                                              6
                                            ]
                                          },
                                          {
                                            "@eq": [
                                              {
                                                "@length": {
                                                  "$var": "_groups"
                                                }
                                              },
                                              3
                                            ]
                                          },
                                          {
                                            "@eq": [
                                              {
                                                "@length": {
                                                  "$var": "_pairs"
                                                }
                                              },
                                              3
                                            ]
                                          },
                                          {
                                            "$var": "_consecutive"
                                          }
                                        ]
                                      },
                                      "else": {
                                        "$if": {
                                          "when": {
                                            "@eq": [
                                              {
                                                "$arg": "kind"
                                              },
                                              7
                                            ]
                                          },
                                          "then": {
                                            "$and": [
                                              {
                                                "@eq": [
                                                  {
                                                    "$var": "_n"
                                                  },
                                                  6
                                                ]
                                              },
                                              {
                                                "@eq": [
                                                  {
                                                    "@length": {
                                                      "$var": "_groups"
                                                    }
                                                  },
                                                  2
                                                ]
                                              },
                                              {
                                                "@eq": [
                                                  {
                                                    "@length": {
                                                      "$var": "_triples"
                                                    }
                                                  },
                                                  2
                                                ]
                                              },
                                              {
                                                "$var": "_consecutive"
                                              }
                                            ]
                                          },
                                          "else": {
                                            "$if": {
                                              "when": {
                                                "@eq": [
                                                  {
                                                    "$arg": "kind"
                                                  },
                                                  8
                                                ]
                                              },
                                              "then": {
                                                "$and": [
                                                  {
                                                    "@gte": [
                                                      {
                                                        "$var": "_n"
                                                      },
                                                      4
                                                    ]
                                                  },
                                                  {
                                                    "@lte": [
                                                      {
                                                        "$var": "_n"
                                                      },
                                                      10
                                                    ]
                                                  },
                                                  {
                                                    "@eq": [
                                                      {
                                                        "@length": {
                                                          "$var": "_groups"
                                                        }
                                                      },
                                                      1
                                                    ]
                                                  },
                                                  {
                                                    "@lte": [
                                                      {
                                                        "$var": "_base"
                                                      },
                                                      14
                                                    ]
                                                  }
                                                ]
                                              },
                                              "else": {
                                                "$if": {
                                                  "when": {
                                                    "@eq": [
                                                      {
                                                        "$arg": "kind"
                                                      },
                                                      10
                                                    ]
                                                  },
                                                  "then": {
                                                    "$and": [
                                                      {
                                                        "@eq": [
                                                          {
                                                            "$var": "_n"
                                                          },
                                                          4
                                                        ]
                                                      },
                                                      {
                                                        "@eq": [
                                                          {
                                                            "$count": {
                                                              "items": {
                                                                "$var": "_cards"
                                                              },
                                                              "as": "_j",
                                                              "where": {
                                                                "@contains": [
                                                                  [
                                                                    "BJ#1",
                                                                    "BJ#2",
                                                                    "RJ#1",
                                                                    "RJ#2"
                                                                  ],
                                                                  {
                                                                    "$var": "_j"
                                                                  }
                                                                ]
                                                              }
                                                            }
                                                          },
                                                          4
                                                        ]
                                                      }
                                                    ]
                                                  },
                                                  "else": false
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
                  }
                }
              }
            },
            {
              "name": "_valid",
              "value": {
                "$and": [
                  {
                    "$var": "_shapeValid"
                  },
                  {
                    "$or": [
                      {
                        "@contains": [
                          [
                            5,
                            6,
                            7,
                            9
                          ],
                          {
                            "$arg": "kind"
                          }
                        ]
                      },
                      {
                        "$not": {
                          "$arg": "aceLow"
                        }
                      }
                    ]
                  },
                  {
                    "@ne": [
                      {
                        "$arg": "wildRank1"
                      },
                      1
                    ]
                  },
                  {
                    "@ne": [
                      {
                        "$arg": "wildRank2"
                      },
                      1
                    ]
                  }
                ]
              }
            },
            {
              "name": "_power",
              "value": {
                "$if": {
                  "when": {
                    "@eq": [
                      {
                        "$arg": "kind"
                      },
                      10
                    ]
                  },
                  "then": 20,
                  "else": {
                    "$if": {
                      "when": {
                        "@eq": [
                          {
                            "$arg": "kind"
                          },
                          9
                        ]
                      },
                      "then": 3,
                      "else": {
                        "$if": {
                          "when": {
                            "@eq": [
                              {
                                "$arg": "kind"
                              },
                              8
                            ]
                          },
                          "then": {
                            "$if": {
                              "when": {
                                "@gte": [
                                  {
                                    "$var": "_n"
                                  },
                                  6
                                ]
                              },
                              "then": {
                                "$var": "_n"
                              },
                              "else": {
                                "@subtract": [
                                  {
                                    "$var": "_n"
                                  },
                                  3
                                ]
                              }
                            }
                          },
                          "else": 0
                        }
                      }
                    }
                  }
                }
              }
            },
            {
              "name": "_strength",
              "value": {
                "$if": {
                  "when": {
                    "@contains": [
                      [
                        5,
                        6,
                        7,
                        9
                      ],
                      {
                        "$arg": "kind"
                      }
                    ]
                  },
                  "then": {
                    "$var": "_top"
                  },
                  "else": {
                    "$let": {
                      "bindings": [
                        {
                          "name": "_rank",
                          "value": {
                            "$if": {
                              "when": {
                                "@eq": [
                                  {
                                    "$arg": "kind"
                                  },
                                  4
                                ]
                              },
                              "then": {
                                "$if": {
                                  "when": {
                                    "@gt": [
                                      {
                                        "@length": {
                                          "$var": "_triples"
                                        }
                                      },
                                      0
                                    ]
                                  },
                                  "then": {
                                    "@get": [
                                      {
                                        "@first": {
                                          "$var": "_triples"
                                        }
                                      },
                                      "key"
                                    ]
                                  },
                                  "else": 0
                                }
                              },
                              "else": {
                                "$var": "_base"
                              }
                            }
                          }
                        }
                      ],
                      "body": {
                        "$call": "rank_strength"
                      }
                    }
                  }
                }
              }
            }
          ],
          "body": {
            "$rank_vector": {
              "category": [
                {
                  "$if": {
                    "when": {
                      "$var": "_valid"
                    },
                    "then": 1,
                    "else": 0
                  }
                },
                {
                  "$arg": "kind"
                },
                {
                  "$var": "_power"
                }
              ],
              "tieBreakers": [
                {
                  "$var": "_strength"
                }
              ]
            }
          }
        }
      }
    },
    "play_valid": {
      "returns": "number",
      "body": {
        "@at": [
          {
            "@get": [
              {
                "$call": "play_descriptor"
              },
              "category"
            ]
          },
          0
        ]
      }
    },
    "play_power": {
      "returns": "number",
      "body": {
        "@at": [
          {
            "@get": [
              {
                "$call": "play_descriptor"
              },
              "category"
            ]
          },
          2
        ]
      }
    },
    "play_strength": {
      "returns": "number",
      "body": {
        "@at": [
          {
            "@get": [
              {
                "$call": "play_descriptor"
              },
              "tieBreakers"
            ]
          },
          0
        ]
      }
    },
    "players_with_cards": {
      "returns": "player_id[]",
      "body": {
        "$filter": {
          "items": {
            "$path": "players"
          },
          "as": "_remainingPlayer",
          "where": {
            "@gt": [
              {
                "@length": {
                  "$zone": [
                    "hands",
                    {
                      "$var": "_remainingPlayer"
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
    "partner": {
      "returns": "player_id[]",
      "body": [
        {
          "@at": [
            {
              "$path": "players"
            },
            {
              "@mod": [
                {
                  "@add": [
                    {
                      "@index_of": [
                        {
                          "$path": "players"
                        },
                        {
                          "$var": "_player"
                        }
                      ]
                    },
                    2
                  ]
                },
                4
              ]
            }
          ]
        }
      ]
    },
    "player_team": {
      "returns": "player_id[]",
      "body": {
        "$filter": {
          "items": {
            "$path": "players"
          },
          "as": "_member",
          "where": {
            "@eq": [
              {
                "@mod": [
                  {
                    "@index_of": [
                      {
                        "$path": "players"
                      },
                      {
                        "$var": "_member"
                      }
                    ]
                  },
                  2
                ]
              },
              {
                "@mod": [
                  {
                    "@index_of": [
                      {
                        "$path": "players"
                      },
                      {
                        "$var": "_player"
                      }
                    ]
                  },
                  2
                ]
              }
            ]
          }
        }
      }
    },
    "response_order": {
      "returns": "player_id[]",
      "body": {
        "$filter": {
          "items": {
            "@concat": [
              {
                "@slice": [
                  {
                    "$path": "players"
                  },
                  {
                    "@mod": [
                      {
                        "@add": [
                          {
                            "@index_of": [
                              {
                                "$path": "players"
                              },
                              {
                                "$var": "_actor"
                              }
                            ]
                          },
                          1
                        ]
                      },
                      4
                    ]
                  },
                  4
                ]
              },
              {
                "@slice": [
                  {
                    "$path": "players"
                  },
                  0,
                  {
                    "@mod": [
                      {
                        "@add": [
                          {
                            "@index_of": [
                              {
                                "$path": "players"
                              },
                              {
                                "$var": "_actor"
                              }
                            ]
                          },
                          1
                        ]
                      },
                      4
                    ]
                  }
                ]
              }
            ]
          },
          "as": "_nextPlayer",
          "where": {
            "$and": [
              {
                "@gt": [
                  {
                    "@length": {
                      "$zone": [
                        "hands",
                        {
                          "$var": "_nextPlayer"
                        }
                      ]
                    }
                  },
                  0
                ]
              },
              {
                "@ne": [
                  {
                    "$var": "_nextPlayer"
                  },
                  {
                    "$var": "_actor"
                  }
                ]
              }
            ]
          }
        }
      }
    },
    "tribute_players": {
      "returns": "player_id[]",
      "body": {
        "$if": {
          "when": {
            "@eq": [
              {
                "@length": {
                  "$path": "variables.previousOrder"
                }
              },
              4
            ]
          },
          "then": {
            "$if": {
              "when": {
                "@eq": [
                  {
                    "@at": [
                      {
                        "$path": "players"
                      },
                      {
                        "@mod": [
                          {
                            "@add": [
                              {
                                "@index_of": [
                                  {
                                    "$path": "players"
                                  },
                                  {
                                    "@at": [
                                      {
                                        "$path": "variables.previousOrder"
                                      },
                                      0
                                    ]
                                  }
                                ]
                              },
                              2
                            ]
                          },
                          4
                        ]
                      }
                    ]
                  },
                  {
                    "@at": [
                      {
                        "$path": "variables.previousOrder"
                      },
                      1
                    ]
                  }
                ]
              },
              "then": {
                "@slice": [
                  {
                    "$path": "variables.previousOrder"
                  },
                  2,
                  4
                ]
              },
              "else": [
                {
                  "@at": [
                    {
                      "$path": "variables.previousOrder"
                    },
                    3
                  ]
                }
              ]
            }
          },
          "else": []
        }
      }
    },
    "deal_order": {
      "returns": "player_id[]",
      "body": {
        "$if": {
          "when": {
            "@eq": [
              {
                "@length": {
                  "$path": "variables.previousOrder"
                }
              },
              4
            ]
          },
          "then": {
            "@concat": [
              {
                "@slice": [
                  {
                    "$path": "players"
                  },
                  {
                    "$if": {
                      "when": {
                        "@eq": [
                          {
                            "@length": {
                              "$call": "tribute_players"
                            }
                          },
                          2
                        ]
                      },
                      "then": {
                        "@mod": [
                          {
                            "@add": [
                              {
                                "@index_of": [
                                  {
                                    "$path": "players"
                                  },
                                  {
                                    "@first": {
                                      "$path": "variables.previousOrder"
                                    }
                                  }
                                ]
                              },
                              1
                            ]
                          },
                          4
                        ]
                      },
                      "else": {
                        "@index_of": [
                          {
                            "$path": "players"
                          },
                          {
                            "@at": [
                              {
                                "$path": "variables.previousOrder"
                              },
                              3
                            ]
                          }
                        ]
                      }
                    }
                  },
                  4
                ]
              },
              {
                "@slice": [
                  {
                    "$path": "players"
                  },
                  0,
                  {
                    "$if": {
                      "when": {
                        "@eq": [
                          {
                            "@length": {
                              "$call": "tribute_players"
                            }
                          },
                          2
                        ]
                      },
                      "then": {
                        "@mod": [
                          {
                            "@add": [
                              {
                                "@index_of": [
                                  {
                                    "$path": "players"
                                  },
                                  {
                                    "@first": {
                                      "$path": "variables.previousOrder"
                                    }
                                  }
                                ]
                              },
                              1
                            ]
                          },
                          4
                        ]
                      },
                      "else": {
                        "@index_of": [
                          {
                            "$path": "players"
                          },
                          {
                            "@at": [
                              {
                                "$path": "variables.previousOrder"
                              },
                              3
                            ]
                          }
                        ]
                      }
                    }
                  }
                ]
              }
            ]
          },
          "else": {
            "$path": "players"
          }
        }
      }
    },
    "give_tribute_condition": {
      "returns": "number",
      "body": {
        "$if": {
          "when": {
            "@contains": [
              {
                "$argmax": {
                  "items": {
                    "$filter": {
                      "items": {
                        "$zone": [
                          "hands",
                          {
                            "$var": "_actor"
                          }
                        ]
                      },
                      "as": "_card",
                      "where": {
                        "@eq": [
                          {
                            "$call": "is_wild"
                          },
                          0
                        ]
                      }
                    }
                  },
                  "as": "_card",
                  "by": {
                    "$call": "card_strength"
                  }
                }
              },
              {
                "$arg": "card"
              }
            ]
          },
          "then": 1,
          "else": 0
        }
      }
    },
    "return_tribute_condition": {
      "returns": "number",
      "body": {
        "$if": {
          "when": {
            "@contains": [
              {
                "$if": {
                  "when": {
                    "@gt": [
                      {
                        "@length": {
                          "$filter": {
                            "items": {
                              "$zone": [
                                "hands",
                                {
                                  "$var": "_actor"
                                }
                              ]
                            },
                            "as": "_card",
                            "where": {
                              "@lte": [
                                {
                                  "$call": "card_strength"
                                },
                                10
                              ]
                            }
                          }
                        }
                      },
                      0
                    ]
                  },
                  "then": {
                    "$filter": {
                      "items": {
                        "$zone": [
                          "hands",
                          {
                            "$var": "_actor"
                          }
                        ]
                      },
                      "as": "_card",
                      "where": {
                        "@lte": [
                          {
                            "$call": "card_strength"
                          },
                          10
                        ]
                      }
                    }
                  },
                  "else": {
                    "$let": {
                      "bindings": [
                        {
                          "name": "_card",
                          "value": {
                            "@first": {
                              "$sort": {
                                "items": {
                                  "$zone": [
                                    "hands",
                                    {
                                      "$var": "_actor"
                                    }
                                  ]
                                },
                                "as": "_card",
                                "by": {
                                  "$call": "card_strength"
                                },
                                "order": "asc"
                              }
                            }
                          }
                        },
                        {
                          "name": "_minStrength",
                          "value": {
                            "$call": "card_strength"
                          }
                        }
                      ],
                      "body": {
                        "$filter": {
                          "items": {
                            "$zone": [
                              "hands",
                              {
                                "$var": "_actor"
                              }
                            ]
                          },
                          "as": "_card",
                          "where": {
                            "@eq": [
                              {
                                "$call": "card_strength"
                              },
                              {
                                "$var": "_minStrength"
                              }
                            ]
                          }
                        }
                      }
                    }
                  }
                }
              },
              {
                "$arg": "card"
              }
            ]
          },
          "then": 1,
          "else": 0
        }
      }
    },
    "play_cards_condition": {
      "returns": "number",
      "body": {
        "$if": {
          "when": {
            "$if": {
              "when": {
                "$and": [
                  {
                    "@gt": [
                      {
                        "@length": {
                          "$filter": {
                            "items": [
                              {
                                "$arg": "card1"
                              },
                              {
                                "$arg": "card2"
                              },
                              {
                                "$arg": "card3"
                              },
                              {
                                "$arg": "card4"
                              },
                              {
                                "$arg": "card5"
                              },
                              {
                                "$arg": "card6"
                              },
                              {
                                "$arg": "card7"
                              },
                              {
                                "$arg": "card8"
                              },
                              {
                                "$arg": "card9"
                              },
                              {
                                "$arg": "card10"
                              }
                            ],
                            "as": "_selectedCard",
                            "where": {
                              "@ne": [
                                {
                                  "$var": "_selectedCard"
                                },
                                ""
                              ]
                            }
                          }
                        }
                      },
                      0
                    ]
                  },
                  {
                    "@eq": [
                      {
                        "@length": {
                          "$filter": {
                            "items": [
                              {
                                "$arg": "card1"
                              },
                              {
                                "$arg": "card2"
                              },
                              {
                                "$arg": "card3"
                              },
                              {
                                "$arg": "card4"
                              },
                              {
                                "$arg": "card5"
                              },
                              {
                                "$arg": "card6"
                              },
                              {
                                "$arg": "card7"
                              },
                              {
                                "$arg": "card8"
                              },
                              {
                                "$arg": "card9"
                              },
                              {
                                "$arg": "card10"
                              }
                            ],
                            "as": "_selectedCard",
                            "where": {
                              "@ne": [
                                {
                                  "$var": "_selectedCard"
                                },
                                ""
                              ]
                            }
                          }
                        }
                      },
                      {
                        "@length": {
                          "@unique": {
                            "$filter": {
                              "items": [
                                {
                                  "$arg": "card1"
                                },
                                {
                                  "$arg": "card2"
                                },
                                {
                                  "$arg": "card3"
                                },
                                {
                                  "$arg": "card4"
                                },
                                {
                                  "$arg": "card5"
                                },
                                {
                                  "$arg": "card6"
                                },
                                {
                                  "$arg": "card7"
                                },
                                {
                                  "$arg": "card8"
                                },
                                {
                                  "$arg": "card9"
                                },
                                {
                                  "$arg": "card10"
                                }
                              ],
                              "as": "_selectedCard",
                              "where": {
                                "@ne": [
                                  {
                                    "$var": "_selectedCard"
                                  },
                                  ""
                                ]
                              }
                            }
                          }
                        }
                      }
                    ]
                  },
                  {
                    "@eq": [
                      {
                        "$count": {
                          "items": {
                            "$filter": {
                              "items": [
                                {
                                  "$arg": "card1"
                                },
                                {
                                  "$arg": "card2"
                                },
                                {
                                  "$arg": "card3"
                                },
                                {
                                  "$arg": "card4"
                                },
                                {
                                  "$arg": "card5"
                                },
                                {
                                  "$arg": "card6"
                                },
                                {
                                  "$arg": "card7"
                                },
                                {
                                  "$arg": "card8"
                                },
                                {
                                  "$arg": "card9"
                                },
                                {
                                  "$arg": "card10"
                                }
                              ],
                              "as": "_selectedCard",
                              "where": {
                                "@ne": [
                                  {
                                    "$var": "_selectedCard"
                                  },
                                  ""
                                ]
                              }
                            }
                          },
                          "as": "_ownedCard",
                          "where": {
                            "@contains": [
                              {
                                "$zone": [
                                  "hands",
                                  {
                                    "$var": "_actor"
                                  }
                                ]
                              },
                              {
                                "$var": "_ownedCard"
                              }
                            ]
                          }
                        }
                      },
                      {
                        "@length": {
                          "$filter": {
                            "items": [
                              {
                                "$arg": "card1"
                              },
                              {
                                "$arg": "card2"
                              },
                              {
                                "$arg": "card3"
                              },
                              {
                                "$arg": "card4"
                              },
                              {
                                "$arg": "card5"
                              },
                              {
                                "$arg": "card6"
                              },
                              {
                                "$arg": "card7"
                              },
                              {
                                "$arg": "card8"
                              },
                              {
                                "$arg": "card9"
                              },
                              {
                                "$arg": "card10"
                              }
                            ],
                            "as": "_selectedCard",
                            "where": {
                              "@ne": [
                                {
                                  "$var": "_selectedCard"
                                },
                                ""
                              ]
                            }
                          }
                        }
                      }
                    ]
                  }
                ]
              },
              "then": {
                "$and": [
                  {
                    "@eq": [
                      {
                        "$call": "play_valid"
                      },
                      1
                    ]
                  },
                  {
                    "$if": {
                      "when": {
                        "@eq": [
                          {
                            "$path": "variables.lastKind"
                          },
                          0
                        ]
                      },
                      "then": true,
                      "else": {
                        "$if": {
                          "when": {
                            "@eq": [
                              {
                                "$call": "play_power"
                              },
                              0
                            ]
                          },
                          "then": {
                            "$and": [
                              {
                                "@eq": [
                                  {
                                    "$path": "variables.lastPower"
                                  },
                                  0
                                ]
                              },
                              {
                                "@eq": [
                                  {
                                    "$arg": "kind"
                                  },
                                  {
                                    "$path": "variables.lastKind"
                                  }
                                ]
                              },
                              {
                                "@gt": [
                                  {
                                    "$call": "play_strength"
                                  },
                                  {
                                    "$path": "variables.lastStrength"
                                  }
                                ]
                              }
                            ]
                          },
                          "else": {
                            "$or": [
                              {
                                "@gt": [
                                  {
                                    "$call": "play_power"
                                  },
                                  {
                                    "$path": "variables.lastPower"
                                  }
                                ]
                              },
                              {
                                "$and": [
                                  {
                                    "@eq": [
                                      {
                                        "$call": "play_power"
                                      },
                                      {
                                        "$path": "variables.lastPower"
                                      }
                                    ]
                                  },
                                  {
                                    "@gt": [
                                      {
                                        "$call": "play_strength"
                                      },
                                      {
                                        "$path": "variables.lastStrength"
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
                  }
                ]
              },
              "else": false
            }
          },
          "then": 1,
          "else": 0
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
                "zone": "pool"
              }
            },
            {
              "op": "$move_all",
              "source": {
                "zone": [
                  "tableau1",
                  {
                    "$var": "_player"
                  }
                ]
              },
              "target": {
                "zone": "pool"
              }
            },
            {
              "op": "$move_all",
              "source": {
                "zone": [
                  "tableau2",
                  {
                    "$var": "_player"
                  }
                ]
              },
              "target": {
                "zone": "pool"
              }
            }
          ]
        },
        {
          "op": "$move_all",
          "source": {
            "zone": "deck"
          },
          "target": {
            "zone": "pool"
          }
        },
        {
          "op": "$move_all",
          "source": {
            "zone": "table"
          },
          "target": {
            "zone": "pool"
          }
        },
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
          "op": "$if",
          "when": {
            "@eq": [
              {
                "$path": "round"
              },
              0
            ]
          },
          "effects": [
            {
              "op": "$move_cards",
              "source": {
                "zone": "pool"
              },
              "target": {
                "zone": "table"
              },
              "cards": {
                "$filter": {
                  "items": {
                    "$zone": "pool"
                  },
                  "as": "_card",
                  "where": {
                    "$if": {
                      "when": {
                        "@contains": [
                          [
                            "BJ#1",
                            "BJ#2",
                            "RJ#1",
                            "RJ#2"
                          ],
                          {
                            "$var": "_card"
                          }
                        ]
                      },
                      "then": false,
                      "else": {
                        "@ne": [
                          {
                            "$call": "is_wild"
                          },
                          1
                        ]
                      }
                    }
                  }
                }
              }
            },
            {
              "op": "$draw",
              "source": {
                "zone": "table"
              },
              "target": {
                "zone": "discard"
              },
              "count": 1,
              "from": "random"
            },
            {
              "op": "$set",
              "path": "variables.anchorCard",
              "value": {
                "@first": {
                  "$zone": "discard"
                }
              }
            },
            {
              "op": "$move_all",
              "source": {
                "zone": "table"
              },
              "target": {
                "zone": "pool"
              }
            },
            {
              "op": "$move_all",
              "source": {
                "zone": "discard"
              },
              "target": {
                "zone": "pool"
              }
            }
          ]
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
          "path": "variables.finishOrder",
          "value": []
        },
        {
          "op": "$set",
          "path": "variables.lastKind",
          "value": 0
        },
        {
          "op": "$set",
          "path": "variables.lastPower",
          "value": 0
        },
        {
          "op": "$set",
          "path": "variables.lastStrength",
          "value": 0
        },
        {
          "op": "$set",
          "path": "pendingPlayers",
          "value": []
        },
        {
          "op": "$for_each_player",
          "effects": [
            {
              "op": "$set",
              "path": [
                "variables",
                "tributeTo",
                {
                  "$var": "_player"
                }
              ],
              "value": {
                "$var": "_player"
              }
            },
            {
              "op": "$set",
              "path": [
                "variables",
                "tributeFrom",
                {
                  "$var": "_player"
                }
              ],
              "value": {
                "$var": "_player"
              }
            },
            {
              "op": "$set",
              "path": [
                "variables",
                "tributeFace",
                {
                  "$var": "_player"
                }
              ],
              "value": ""
            },
            {
              "op": "$set",
              "path": [
                "variables",
                "antiTributeKingCount",
                {
                  "$var": "_player"
                }
              ],
              "value": 0
            }
          ]
        },
        {
          "op": "$add",
          "path": "round",
          "value": 1
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "dealing"
        }
      ]
    },
    {
      "type": "deal_cards",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "dealing"
        ]
      },
      "effects": [
        {
          "op": "$for_each",
          "items": [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27
          ],
          "as": "_dealPass",
          "effects": [
            {
              "op": "$for_each",
              "items": {
                "$call": "deal_order"
              },
              "as": "_player",
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
                  "from": "head"
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
                  "$path": "variables.previousOrder"
                }
              },
              0
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "variables.openingPlayer",
              "value": {
                "@first": {
                  "$filter": {
                    "items": {
                      "$path": "players"
                    },
                    "as": "_p",
                    "where": {
                      "@contains": [
                        {
                          "$zone": [
                            "hands",
                            {
                              "$var": "_p"
                            }
                          ]
                        },
                        {
                          "$path": "variables.anchorCard"
                        }
                      ]
                    }
                  }
                }
              }
            },
            {
              "op": "$set",
              "path": "variables.turn",
              "value": {
                "$path": "variables.openingPlayer"
              }
            },
            {
              "op": "$set",
              "path": "phase",
              "value": "playing"
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "@eq": [
              {
                "@length": {
                  "$path": "variables.previousOrder"
                }
              },
              4
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "check_tribute"
            }
          ]
        }
      ]
    },
    {
      "type": "check_tribute",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "check_tribute"
        ]
      },
      "effects": [
        {
          "op": "$if",
          "when": {
            "@eq": [
              {
                "$sum": {
                  "items": {
                    "$call": "tribute_players"
                  },
                  "as": "_p",
                  "by": {
                    "$count": {
                      "items": {
                        "$zone": [
                          "hands",
                          {
                            "$var": "_p"
                          }
                        ]
                      },
                      "as": "_card",
                      "where": {
                        "@contains": [
                          [
                            "RJ#1",
                            "RJ#2"
                          ],
                          {
                            "$var": "_card"
                          }
                        ]
                      }
                    }
                  }
                }
              },
              2
            ]
          },
          "effects": [
            {
              "op": "$for_each",
              "items": {
                "$call": "tribute_players"
              },
              "as": "_player",
              "effects": [
                {
                  "op": "$set",
                  "path": [
                    "variables",
                    "antiTributeKingCount",
                    {
                      "$var": "_player"
                    }
                  ],
                  "value": {
                    "$count": {
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
                        "@contains": [
                          [
                            "RJ#1",
                            "RJ#2"
                          ],
                          {
                            "$var": "_card"
                          }
                        ]
                      }
                    }
                  }
                },
                {
                  "op": "$if",
                  "when": {
                    "@gt": [
                      {
                        "$count": {
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
                            "@contains": [
                              [
                                "RJ#1",
                                "RJ#2"
                              ],
                              {
                                "$var": "_card"
                              }
                            ]
                          }
                        }
                      },
                      0
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
                        "zone": [
                          "tableau1",
                          {
                            "$var": "_player"
                          }
                        ]
                      },
                      "cards": {
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
                            "@contains": [
                              [
                                "RJ#1",
                                "RJ#2"
                              ],
                              {
                                "$var": "_card"
                              }
                            ]
                          }
                        }
                      }
                    },
                    {
                      "op": "$reveal",
                      "source": {
                        "zone": [
                          "tableau1",
                          {
                            "$var": "_player"
                          }
                        ]
                      }
                    },
                    {
                      "op": "$move_all",
                      "source": {
                        "zone": [
                          "tableau1",
                          {
                            "$var": "_player"
                          }
                        ]
                      },
                      "target": {
                        "zone": [
                          "hands",
                          {
                            "$var": "_player"
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
              "path": "variables.openingPlayer",
              "value": {
                "@first": {
                  "$path": "variables.previousOrder"
                }
              }
            },
            {
              "op": "$set",
              "path": "variables.turn",
              "value": {
                "$path": "variables.openingPlayer"
              }
            },
            {
              "op": "$set",
              "path": "phase",
              "value": "playing"
            }
          ]
        },
        {
          "op": "$if",
          "when": {
            "$and": [
              {
                "@eq": [
                  {
                    "$path": "phase"
                  },
                  "check_tribute"
                ]
              },
              {
                "$not": {
                  "@eq": [
                    {
                      "$sum": {
                        "items": {
                          "$call": "tribute_players"
                        },
                        "as": "_p",
                        "by": {
                          "$count": {
                            "items": {
                              "$zone": [
                                "hands",
                                {
                                  "$var": "_p"
                                }
                              ]
                            },
                            "as": "_card",
                            "where": {
                              "@contains": [
                                [
                                  "RJ#1",
                                  "RJ#2"
                                ],
                                {
                                  "$var": "_card"
                                }
                              ]
                            }
                          }
                        }
                      }
                    },
                    2
                  ]
                }
              }
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "pendingPlayers",
              "value": {
                "$call": "tribute_players"
              }
            },
            {
              "op": "$set",
              "path": "phase",
              "value": "giving_tribute"
            }
          ]
        }
      ]
    },
    {
      "type": "give_tribute",
      "actor": "player",
      "args": [
        {
          "name": "card",
          "type": "string",
          "required": true
        }
      ],
      "when": {
        "$if": {
          "when": {
            "$and": [
              {
                "@eq": [
                  {
                    "$path": "phase"
                  },
                  "giving_tribute"
                ]
              },
              {
                "@eq": [
                  {
                    "$var": "_actor"
                  },
                  {
                    "@first": {
                      "$path": "pendingPlayers"
                    }
                  }
                ]
              }
            ]
          },
          "then": {
            "@eq": [
              {
                "$call": "give_tribute_condition"
              },
              1
            ]
          },
          "else": false
        }
      },
      "effects": [
        {
          "op": "$move_cards",
          "source": {
            "zone": [
              "hands",
              {
                "$var": "_actor"
              }
            ]
          },
          "target": {
            "zone": [
              "tableau1",
              {
                "$var": "_actor"
              }
            ]
          },
          "cards": [
            {
              "$arg": "card"
            }
          ]
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
                  "$path": "pendingPlayers"
                }
              },
              0
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "resolve_tribute"
            }
          ]
        }
      ]
    },
    {
      "type": "resolve_tribute",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "resolve_tribute"
        ]
      },
      "effects": [
        {
          "op": "$if",
          "when": {
            "@eq": [
              {
                "@length": {
                  "$call": "tribute_players"
                }
              },
              1
            ]
          },
          "effects": [
            {
              "op": "$for_each",
              "items": {
                "$call": "tribute_players"
              },
              "as": "_giver",
              "effects": [
                {
                  "op": "$set",
                  "path": [
                    "variables",
                    "tributeTo",
                    {
                      "$var": "_giver"
                    }
                  ],
                  "value": {
                    "@first": {
                      "$path": "variables.previousOrder"
                    }
                  }
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
                  "$call": "tribute_players"
                }
              },
              2
            ]
          },
          "effects": [
            {
              "op": "$for_each",
              "items": [
                {
                  "@at": [
                    {
                      "$call": "tribute_players"
                    },
                    0
                  ]
                }
              ],
              "as": "_firstGiver",
              "effects": [
                {
                  "op": "$for_each",
                  "items": [
                    {
                      "@at": [
                        {
                          "$call": "tribute_players"
                        },
                        1
                      ]
                    }
                  ],
                  "as": "_secondGiver",
                  "effects": [
                    {
                      "op": "$for_each",
                      "items": {
                        "$call": "tribute_players"
                      },
                      "as": "_giver",
                      "effects": [
                        {
                          "op": "$set",
                          "path": [
                            "variables",
                            "tributeTo",
                            {
                              "$var": "_giver"
                            }
                          ],
                          "value": {
                            "$if": {
                              "when": {
                                "@eq": [
                                  {
                                    "$let": {
                                      "bindings": [
                                        {
                                          "name": "_card",
                                          "value": {
                                            "@first": {
                                              "$zone": [
                                                "tableau1",
                                                {
                                                  "$var": "_firstGiver"
                                                }
                                              ]
                                            }
                                          }
                                        }
                                      ],
                                      "body": {
                                        "$call": "card_strength"
                                      }
                                    }
                                  },
                                  {
                                    "$let": {
                                      "bindings": [
                                        {
                                          "name": "_card",
                                          "value": {
                                            "@first": {
                                              "$zone": [
                                                "tableau1",
                                                {
                                                  "$var": "_secondGiver"
                                                }
                                              ]
                                            }
                                          }
                                        }
                                      ],
                                      "body": {
                                        "$call": "card_strength"
                                      }
                                    }
                                  }
                                ]
                              },
                              "then": {
                                "@at": [
                                  {
                                    "$path": "players"
                                  },
                                  {
                                    "@mod": [
                                      {
                                        "@add": [
                                          {
                                            "@index_of": [
                                              {
                                                "$path": "players"
                                              },
                                              {
                                                "$var": "_giver"
                                              }
                                            ]
                                          },
                                          3
                                        ]
                                      },
                                      4
                                    ]
                                  }
                                ]
                              },
                              "else": {
                                "$if": {
                                  "when": {
                                    "@eq": [
                                      {
                                        "$var": "_giver"
                                      },
                                      {
                                        "$if": {
                                          "when": {
                                            "@gt": [
                                              {
                                                "$let": {
                                                  "bindings": [
                                                    {
                                                      "name": "_card",
                                                      "value": {
                                                        "@first": {
                                                          "$zone": [
                                                            "tableau1",
                                                            {
                                                              "$var": "_firstGiver"
                                                            }
                                                          ]
                                                        }
                                                      }
                                                    }
                                                  ],
                                                  "body": {
                                                    "$call": "card_strength"
                                                  }
                                                }
                                              },
                                              {
                                                "$let": {
                                                  "bindings": [
                                                    {
                                                      "name": "_card",
                                                      "value": {
                                                        "@first": {
                                                          "$zone": [
                                                            "tableau1",
                                                            {
                                                              "$var": "_secondGiver"
                                                            }
                                                          ]
                                                        }
                                                      }
                                                    }
                                                  ],
                                                  "body": {
                                                    "$call": "card_strength"
                                                  }
                                                }
                                              }
                                            ]
                                          },
                                          "then": {
                                            "$var": "_firstGiver"
                                          },
                                          "else": {
                                            "$var": "_secondGiver"
                                          }
                                        }
                                      }
                                    ]
                                  },
                                  "then": {
                                    "@first": {
                                      "$path": "variables.previousOrder"
                                    }
                                  },
                                  "else": {
                                    "@at": [
                                      {
                                        "$path": "variables.previousOrder"
                                      },
                                      1
                                    ]
                                  }
                                }
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
          ]
        },
        {
          "op": "$for_each",
          "items": {
            "$call": "tribute_players"
          },
          "as": "_giver",
          "effects": [
            {
              "op": "$set",
              "path": [
                "variables",
                "tributeFace",
                {
                  "$var": "_giver"
                }
              ],
              "value": {
                "@first": {
                  "$zone": [
                    "tableau1",
                    {
                      "$var": "_giver"
                    }
                  ]
                }
              }
            },
            {
              "op": "$reveal",
              "source": {
                "zone": [
                  "tableau1",
                  {
                    "$var": "_giver"
                  }
                ]
              }
            },
            {
              "op": "$for_each",
              "items": [
                {
                  "$path": [
                    "variables",
                    "tributeTo",
                    {
                      "$var": "_giver"
                    }
                  ]
                }
              ],
              "as": "_receiver",
              "effects": [
                {
                  "op": "$set",
                  "path": [
                    "variables",
                    "tributeFrom",
                    {
                      "$var": "_receiver"
                    }
                  ],
                  "value": {
                    "$var": "_giver"
                  }
                },
                {
                  "op": "$move_all",
                  "source": {
                    "zone": [
                      "tableau1",
                      {
                        "$var": "_giver"
                      }
                    ]
                  },
                  "target": {
                    "zone": [
                      "hands",
                      {
                        "$var": "_receiver"
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
          "path": "variables.openingPlayer",
          "value": {
            "@first": {
              "$filter": {
                "items": {
                  "$call": "tribute_players"
                },
                "as": "_giver",
                "where": {
                  "@eq": [
                    {
                      "$path": [
                        "variables",
                        "tributeTo",
                        {
                          "$var": "_giver"
                        }
                      ]
                    },
                    {
                      "@first": {
                        "$path": "variables.previousOrder"
                      }
                    }
                  ]
                }
              }
            }
          }
        },
        {
          "op": "$set",
          "path": "pendingPlayers",
          "value": {
            "$map": {
              "items": {
                "$call": "tribute_players"
              },
              "as": "_giver",
              "by": {
                "$path": [
                  "variables",
                  "tributeTo",
                  {
                    "$var": "_giver"
                  }
                ]
              }
            }
          }
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "returning_tribute"
        }
      ]
    },
    {
      "type": "return_tribute",
      "actor": "player",
      "args": [
        {
          "name": "card",
          "type": "string",
          "required": true
        }
      ],
      "when": {
        "$if": {
          "when": {
            "$and": [
              {
                "@eq": [
                  {
                    "$path": "phase"
                  },
                  "returning_tribute"
                ]
              },
              {
                "@eq": [
                  {
                    "$var": "_actor"
                  },
                  {
                    "@first": {
                      "$path": "pendingPlayers"
                    }
                  }
                ]
              }
            ]
          },
          "then": {
            "@eq": [
              {
                "$call": "return_tribute_condition"
              },
              1
            ]
          },
          "else": false
        }
      },
      "effects": [
        {
          "op": "$move_cards",
          "source": {
            "zone": [
              "hands",
              {
                "$var": "_actor"
              }
            ]
          },
          "target": {
            "zone": [
              "tableau2",
              {
                "$var": "_actor"
              }
            ]
          },
          "cards": [
            {
              "$arg": "card"
            }
          ]
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
                  "$path": "pendingPlayers"
                }
              },
              0
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "phase",
              "value": "resolve_returns"
            }
          ]
        }
      ]
    },
    {
      "type": "resolve_returns",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "resolve_returns"
        ]
      },
      "effects": [
        {
          "op": "$for_each",
          "items": {
            "$call": "tribute_players"
          },
          "as": "_giver",
          "effects": [
            {
              "op": "$for_each",
              "items": [
                {
                  "$path": [
                    "variables",
                    "tributeTo",
                    {
                      "$var": "_giver"
                    }
                  ]
                }
              ],
              "as": "_receiver",
              "effects": [
                {
                  "op": "$move_all",
                  "source": {
                    "zone": [
                      "tableau2",
                      {
                        "$var": "_receiver"
                      }
                    ]
                  },
                  "target": {
                    "zone": [
                      "hands",
                      {
                        "$var": "_giver"
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
          "path": "variables.turn",
          "value": {
            "$path": "variables.openingPlayer"
          }
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "playing"
        }
      ]
    },
    {
      "type": "play_cards",
      "actor": "player",
      "args": [
        {
          "name": "card1",
          "type": "string",
          "required": true
        },
        {
          "name": "card2",
          "type": "string",
          "required": true
        },
        {
          "name": "card3",
          "type": "string",
          "required": true
        },
        {
          "name": "card4",
          "type": "string",
          "required": true
        },
        {
          "name": "card5",
          "type": "string",
          "required": true
        },
        {
          "name": "card6",
          "type": "string",
          "required": true
        },
        {
          "name": "card7",
          "type": "string",
          "required": true
        },
        {
          "name": "card8",
          "type": "string",
          "required": true
        },
        {
          "name": "card9",
          "type": "string",
          "required": true
        },
        {
          "name": "card10",
          "type": "string",
          "required": true
        },
        {
          "name": "kind",
          "type": "integer",
          "required": true,
          "min": 1,
          "max": 10
        },
        {
          "name": "aceLow",
          "type": "boolean",
          "required": true
        },
        {
          "name": "wildRank1",
          "type": "integer",
          "required": true,
          "min": 0,
          "max": 14
        },
        {
          "name": "wildRank2",
          "type": "integer",
          "required": true,
          "min": 0,
          "max": 14
        },
        {
          "name": "wildSuit1",
          "type": "integer",
          "required": true,
          "min": 0,
          "max": 4
        },
        {
          "name": "wildSuit2",
          "type": "integer",
          "required": true,
          "min": 0,
          "max": 4
        }
      ],
      "when": {
        "$if": {
          "when": {
            "$and": [
              {
                "@eq": [
                  {
                    "$path": "phase"
                  },
                  "playing"
                ]
              },
              {
                "@eq": [
                  {
                    "$var": "_actor"
                  },
                  {
                    "$path": "variables.turn"
                  }
                ]
              }
            ]
          },
          "then": {
            "@eq": [
              {
                "$call": "play_cards_condition"
              },
              1
            ]
          },
          "else": false
        }
      },
      "effects": [
        {
          "op": "$set",
          "path": "variables.lastKind",
          "value": {
            "$arg": "kind"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastPower",
          "value": {
            "$call": "play_power"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastStrength",
          "value": {
            "$call": "play_strength"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastPlayer",
          "value": {
            "$var": "_actor"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastWildRank1",
          "value": {
            "$arg": "wildRank1"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastWildRank2",
          "value": {
            "$arg": "wildRank2"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastWildSuit1",
          "value": {
            "$arg": "wildSuit1"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastWildSuit2",
          "value": {
            "$arg": "wildSuit2"
          }
        },
        {
          "op": "$set",
          "path": "variables.lastAceLow",
          "value": {
            "$arg": "aceLow"
          }
        },
        {
          "op": "$move_all",
          "source": {
            "zone": "table"
          },
          "target": {
            "zone": "discard"
          }
        },
        {
          "op": "$move_cards",
          "source": {
            "zone": [
              "hands",
              {
                "$var": "_actor"
              }
            ]
          },
          "target": {
            "zone": "table"
          },
          "cards": {
            "$filter": {
              "items": [
                {
                  "$arg": "card1"
                },
                {
                  "$arg": "card2"
                },
                {
                  "$arg": "card3"
                },
                {
                  "$arg": "card4"
                },
                {
                  "$arg": "card5"
                },
                {
                  "$arg": "card6"
                },
                {
                  "$arg": "card7"
                },
                {
                  "$arg": "card8"
                },
                {
                  "$arg": "card9"
                },
                {
                  "$arg": "card10"
                }
              ],
              "as": "_selectedCard",
              "where": {
                "@ne": [
                  {
                    "$var": "_selectedCard"
                  },
                  ""
                ]
              }
            }
          }
        },
        {
          "op": "$if",
          "when": {
            "@eq": [
              {
                "@length": {
                  "$zone": [
                    "hands",
                    {
                      "$var": "_actor"
                    }
                  ]
                }
              },
              0
            ]
          },
          "effects": [
            {
              "op": "$set",
              "path": "variables.finishOrder",
              "value": {
                "@concat": [
                  {
                    "$path": "variables.finishOrder"
                  },
                  [
                    {
                      "$var": "_actor"
                    }
                  ]
                ]
              }
            }
          ]
        },
        {
          "op": "$set",
          "path": "pendingPlayers",
          "value": {
            "$call": "response_order"
          }
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "advancing"
        }
      ]
    },
    {
      "type": "pass",
      "actor": "player",
      "args": [],
      "when": {
        "$and": [
          {
            "@eq": [
              {
                "$path": "phase"
              },
              "playing"
            ]
          },
          {
            "@eq": [
              {
                "$var": "_actor"
              },
              {
                "$path": "variables.turn"
              }
            ]
          },
          {
            "@ne": [
              {
                "$path": "variables.lastKind"
              },
              0
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
          "op": "$remove",
          "path": "pendingPlayers",
          "value": {
            "$var": "_actor"
          }
        },
        {
          "op": "$set",
          "path": "phase",
          "value": "advancing"
        }
      ]
    },
    {
      "type": "advance_play",
      "actor": "system",
      "args": [],
      "when": {
        "@eq": [
          {
            "$path": "phase"
          },
          "advancing"
        ]
      },
      "effects": [
        {
          "op": "$if",
          "when": {
            "$if": {
              "when": {
                "@gte": [
                  {
                    "@length": {
                      "$path": "variables.finishOrder"
                    }
                  },
                  3
                ]
              },
              "then": true,
              "else": {
                "$if": {
                  "when": {
                    "@eq": [
                      {
                        "@length": {
                          "$path": "variables.finishOrder"
                        }
                      },
                      2
                    ]
                  },
                  "then": {
                    "@eq": [
                      {
                        "@at": [
                          {
                            "$path": "players"
                          },
                          {
                            "@mod": [
                              {
                                "@add": [
                                  {
                                    "@index_of": [
                                      {
                                        "$path": "players"
                                      },
                                      {
                                        "@first": {
                                          "$path": "variables.finishOrder"
                                        }
                                      }
                                    ]
                                  },
                                  2
                                ]
                              },
                              4
                            ]
                          }
                        ]
                      },
                      {
                        "@at": [
                          {
                            "$path": "variables.finishOrder"
                          },
                          1
                        ]
                      }
                    ]
                  },
                  "else": false
                }
              }
            }
          },
          "effects": [
            {
              "op": "$set",
              "path": "pendingPlayers",
              "value": []
            },
            {
              "op": "$set",
              "path": "phase",
              "value": "round_end"
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
              "advancing"
            ]
          },
          "effects": [
            {
              "op": "$if",
              "when": {
                "@gt": [
                  {
                    "@length": {
                      "$path": "pendingPlayers"
                    }
                  },
                  0
                ]
              },
              "effects": [
                {
                  "op": "$set",
                  "path": "variables.turn",
                  "value": {
                    "@first": {
                      "$path": "pendingPlayers"
                    }
                  }
                },
                {
                  "op": "$set",
                  "path": "phase",
                  "value": "playing"
                }
              ]
            },
            {
              "op": "$if",
              "when": {
                "$and": [
                  {
                    "@eq": [
                      {
                        "$path": "phase"
                      },
                      "advancing"
                    ]
                  },
                  {
                    "@eq": [
                      {
                        "@length": {
                          "$path": "pendingPlayers"
                        }
                      },
                      0
                    ]
                  }
                ]
              },
              "effects": [
                {
                  "op": "$for_each",
                  "items": [
                    {
                      "$path": "variables.lastPlayer"
                    }
                  ],
                  "as": "_lastPlayer",
                  "effects": [
                    {
                      "op": "$set",
                      "path": "variables.turn",
                      "value": {
                        "$if": {
                          "when": {
                            "@gt": [
                              {
                                "@length": {
                                  "$zone": [
                                    "hands",
                                    {
                                      "$var": "_lastPlayer"
                                    }
                                  ]
                                }
                              },
                              0
                            ]
                          },
                          "then": {
                            "$var": "_lastPlayer"
                          },
                          "else": {
                            "@at": [
                              {
                                "$path": "players"
                              },
                              {
                                "@mod": [
                                  {
                                    "@add": [
                                      {
                                        "@index_of": [
                                          {
                                            "$path": "players"
                                          },
                                          {
                                            "$var": "_lastPlayer"
                                          }
                                        ]
                                      },
                                      2
                                    ]
                                  },
                                  4
                                ]
                              }
                            ]
                          }
                        }
                      }
                    }
                  ]
                },
                {
                  "op": "$move_all",
                  "source": {
                    "zone": "table"
                  },
                  "target": {
                    "zone": "discard"
                  }
                },
                {
                  "op": "$set",
                  "path": "variables.lastKind",
                  "value": 0
                },
                {
                  "op": "$set",
                  "path": "variables.lastPower",
                  "value": 0
                },
                {
                  "op": "$set",
                  "path": "variables.lastStrength",
                  "value": 0
                },
                {
                  "op": "$set",
                  "path": "phase",
                  "value": "playing"
                }
              ]
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
          "round_end"
        ]
      },
      "effects": [
        {
          "op": "$set",
          "path": "variables.finishOrder",
          "value": {
            "@concat": [
              {
                "$path": "variables.finishOrder"
              },
              {
                "$call": "players_with_cards"
              }
            ]
          }
        },
        {
          "op": "$for_each",
          "items": [
            {
              "@first": {
                "$path": "variables.finishOrder"
              }
            }
          ],
          "as": "_winnerPlayer",
          "effects": [
            {
              "op": "$if",
              "when": {
                "$and": [
                  {
                    "@eq": [
                      {
                        "$path": "variables.level"
                      },
                      14
                    ]
                  },
                  {
                    "@eq": [
                      {
                        "$path": [
                          "scores",
                          {
                            "$var": "_winnerPlayer"
                          }
                        ]
                      },
                      14
                    ]
                  },
                  {
                    "@lte": [
                      {
                        "@index_of": [
                          {
                            "$path": "variables.finishOrder"
                          },
                          {
                            "@at": [
                              {
                                "$path": "players"
                              },
                              {
                                "@mod": [
                                  {
                                    "@add": [
                                      {
                                        "@index_of": [
                                          {
                                            "$path": "players"
                                          },
                                          {
                                            "$var": "_winnerPlayer"
                                          }
                                        ]
                                      },
                                      2
                                    ]
                                  },
                                  4
                                ]
                              }
                            ]
                          }
                        ]
                      },
                      2
                    ]
                  }
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
                    "$filter": {
                      "items": {
                        "$path": "players"
                      },
                      "as": "_member",
                      "where": {
                        "@eq": [
                          {
                            "@mod": [
                              {
                                "@index_of": [
                                  {
                                    "$path": "players"
                                  },
                                  {
                                    "$var": "_member"
                                  }
                                ]
                              },
                              2
                            ]
                          },
                          {
                            "@mod": [
                              {
                                "@index_of": [
                                  {
                                    "$path": "players"
                                  },
                                  {
                                    "$var": "_winnerPlayer"
                                  }
                                ]
                              },
                              2
                            ]
                          }
                        ]
                      }
                    }
                  }
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
                  "round_end"
                ]
              },
              "effects": [
                {
                  "op": "$for_each",
                  "items": [
                    {
                      "$if": {
                        "when": {
                          "@gt": [
                            {
                              "@add": [
                                {
                                  "$path": [
                                    "scores",
                                    {
                                      "$var": "_winnerPlayer"
                                    }
                                  ]
                                },
                                {
                                  "@subtract": [
                                    4,
                                    {
                                      "@index_of": [
                                        {
                                          "$path": "variables.finishOrder"
                                        },
                                        {
                                          "@at": [
                                            {
                                              "$path": "players"
                                            },
                                            {
                                              "@mod": [
                                                {
                                                  "@add": [
                                                    {
                                                      "@index_of": [
                                                        {
                                                          "$path": "players"
                                                        },
                                                        {
                                                          "$var": "_winnerPlayer"
                                                        }
                                                      ]
                                                    },
                                                    2
                                                  ]
                                                },
                                                4
                                              ]
                                            }
                                          ]
                                        }
                                      ]
                                    }
                                  ]
                                }
                              ]
                            },
                            14
                          ]
                        },
                        "then": 14,
                        "else": {
                          "@add": [
                            {
                              "$path": [
                                "scores",
                                {
                                  "$var": "_winnerPlayer"
                                }
                              ]
                            },
                            {
                              "@subtract": [
                                4,
                                {
                                  "@index_of": [
                                    {
                                      "$path": "variables.finishOrder"
                                    },
                                    {
                                      "@at": [
                                        {
                                          "$path": "players"
                                        },
                                        {
                                          "@mod": [
                                            {
                                              "@add": [
                                                {
                                                  "@index_of": [
                                                    {
                                                      "$path": "players"
                                                    },
                                                    {
                                                      "$var": "_winnerPlayer"
                                                    }
                                                  ]
                                                },
                                                2
                                              ]
                                            },
                                            4
                                          ]
                                        }
                                      ]
                                    }
                                  ]
                                }
                              ]
                            }
                          ]
                        }
                      }
                    }
                  ],
                  "as": "_newLevel",
                  "effects": [
                    {
                      "op": "$for_each",
                      "items": {
                        "$filter": {
                          "items": {
                            "$path": "players"
                          },
                          "as": "_member",
                          "where": {
                            "@eq": [
                              {
                                "@mod": [
                                  {
                                    "@index_of": [
                                      {
                                        "$path": "players"
                                      },
                                      {
                                        "$var": "_member"
                                      }
                                    ]
                                  },
                                  2
                                ]
                              },
                              {
                                "@mod": [
                                  {
                                    "@index_of": [
                                      {
                                        "$path": "players"
                                      },
                                      {
                                        "$var": "_winnerPlayer"
                                      }
                                    ]
                                  },
                                  2
                                ]
                              }
                            ]
                          }
                        }
                      },
                      "as": "_teamMember",
                      "effects": [
                        {
                          "op": "$set",
                          "path": [
                            "scores",
                            {
                              "$var": "_teamMember"
                            }
                          ],
                          "value": {
                            "$var": "_newLevel"
                          }
                        }
                      ]
                    },
                    {
                      "op": "$set",
                      "path": "variables.level",
                      "value": {
                        "$var": "_newLevel"
                      }
                    }
                  ]
                },
                {
                  "op": "$set",
                  "path": "variables.previousOrder",
                  "value": {
                    "$path": "variables.finishOrder"
                  }
                },
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
