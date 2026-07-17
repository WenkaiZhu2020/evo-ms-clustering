# Xerces collision-group graph audit

The 11 duplicate-text and duplicate-embedding groups are retained under the frozen simple-name contract. No class or edge was removed.

* Collision groups: 11; collision classes: 55.
* Directed top-k rows from collision classes: 165.
* Directed rows with identical-embedding ties: 165; tie rule: class_id lexicographic ascending.
* Final edges involving collision classes: 103 / 1681 (0.061273).
* Final intra-group edges: 99; final edges to external classes: 4.

| Group | Members | Intra-group final edges | External final edges |
|---|---:|---:|---:|
| collision_01 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.ObjectFactory; org.apache.xerces.impl.dv.ObjectFactory; org.apache.xerces.parsers.ObjectFactory; org.apache.xerces.xinclude.ObjectFactory; org.apache.xml.serialize.ObjectFactory
| collision_02 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.ObjectFactory$ConfigurationError; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError; org.apache.xerces.parsers.ObjectFactory$ConfigurationError; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError; org.apache.xml.serialize.ObjectFactory$ConfigurationError
| collision_03 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.SecuritySupport; org.apache.xerces.impl.dv.SecuritySupport; org.apache.xerces.parsers.SecuritySupport; org.apache.xerces.xinclude.SecuritySupport; org.apache.xml.serialize.SecuritySupport
| collision_04 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1; org.apache.xerces.xinclude.SecuritySupport$1; org.apache.xml.serialize.SecuritySupport$1
| collision_05 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.SecuritySupport$2; org.apache.xerces.impl.dv.SecuritySupport$2; org.apache.xerces.parsers.SecuritySupport$2; org.apache.xerces.xinclude.SecuritySupport$2; org.apache.xml.serialize.SecuritySupport$2
| collision_06 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.SecuritySupport$3; org.apache.xerces.impl.dv.SecuritySupport$3; org.apache.xerces.parsers.SecuritySupport$3; org.apache.xerces.xinclude.SecuritySupport$3; org.apache.xml.serialize.SecuritySupport$3
| collision_07 | 5 | 9 | 3 |

Members: org.apache.xerces.dom.SecuritySupport$4; org.apache.xerces.impl.dv.SecuritySupport$4; org.apache.xerces.parsers.SecuritySupport$4; org.apache.xerces.xinclude.SecuritySupport$4; org.apache.xml.serialize.SecuritySupport$4
| collision_08 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.SecuritySupport$5; org.apache.xerces.impl.dv.SecuritySupport$5; org.apache.xerces.parsers.SecuritySupport$5; org.apache.xerces.xinclude.SecuritySupport$5; org.apache.xml.serialize.SecuritySupport$5
| collision_09 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.SecuritySupport$6; org.apache.xerces.impl.dv.SecuritySupport$6; org.apache.xerces.parsers.SecuritySupport$6; org.apache.xerces.xinclude.SecuritySupport$6; org.apache.xml.serialize.SecuritySupport$6
| collision_10 | 5 | 9 | 1 |

Members: org.apache.xerces.dom.SecuritySupport$7; org.apache.xerces.impl.dv.SecuritySupport$7; org.apache.xerces.parsers.SecuritySupport$7; org.apache.xerces.xinclude.SecuritySupport$7; org.apache.xml.serialize.SecuritySupport$7
| collision_11 | 5 | 9 | 0 |

Members: org.apache.xerces.dom.SecuritySupport$8; org.apache.xerces.impl.dv.SecuritySupport$8; org.apache.xerces.parsers.SecuritySupport$8; org.apache.xerces.xinclude.SecuritySupport$8; org.apache.xml.serialize.SecuritySupport$8

The report is descriptive evidence of deterministic tie handling, not a reason to deduplicate or retune top-k.
