/* India observed measurement forecasts. No disaster model. NOT HARDWARE VALIDATED. */
#ifndef INDRA_INDIA_MODEL_H
#define INDRA_INDIA_MODEL_H
#include <math.h>
#include <stdint.h>
#define INDRA_INDIA_FEATURES 72
#define INDRA_INDIA_HEADS 3
#define INDRA_DISASTER_OUTPUTS_ENABLED 0
#define INDRA_INDIA_HARDWARE_VALIDATED 0
#define INDRA_INDIA_HORIZON_HOURS 6
enum { INDRA_UNTRAINED=0, INDRA_UNCALIBRATED=1, INDRA_ARCHIVE_CALIBRATED=2, INDRA_OOD=3, INDRA_INVALID_CORE=4 };
/* Status/calibration are research evidence only. No field alerts. */
static inline float indra_tree_0_0(const float *x) {
  if (!isnan(x[3]) && x[3] < 6.19999981f) {
    if (!isnan(x[33]) && x[33] < 5.0999999f) {
      if (isnan(x[4]) || x[4] < 36.0f) {
        return -0.0746152997f;
      } else {
        return 0.174264684f;
      }
    } else {
      if (!isnan(x[70]) && x[70] < 72.7166977f) {
        return 0.837294698f;
      } else {
        return 0.0153099913f;
      }
    }
  } else {
    if (isnan(x[11]) || x[11] < 0.111803398f) {
      if (!isnan(x[8]) && x[8] < 29.5f) {
        return 1.08584559f;
      } else {
        return 4.54735565f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 20.5333004f) {
        return -0.0438414291f;
      } else {
        return 0.720326006f;
      }
    }
  }
}
static inline float indra_tree_0_1(const float *x) {
  if (!isnan(x[33]) && x[33] < 6.19999981f) {
    if (isnan(x[57]) || x[57] < 8.5f) {
      if (isnan(x[4]) || x[4] < 36.0f) {
        return -0.0721248612f;
      } else {
        return 0.115136497f;
      }
    } else {
      return 0.435628265f;
    }
  } else {
    if (!isnan(x[70]) && x[70] < 73.3000031f) {
      if (!isnan(x[66]) && x[66] < 0.5f) {
        return -0.0519891158f;
      } else {
        return 0.531556785f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -0.5f) {
        return 0.103595629f;
      } else {
        return -0.0540331267f;
      }
    }
  }
}
static inline float indra_tree_0_2(const float *x) {
  if (!isnan(x[33]) && x[33] < 5.0999999f) {
    if (isnan(x[57]) || x[57] < 7.19999981f) {
      if (isnan(x[4]) || x[4] < 36.0f) {
        return -0.0739470124f;
      } else {
        return 0.0438252948f;
      }
    } else {
      if (!isnan(x[14]) && x[14] < 51.0f) {
        return 0.394210607f;
      } else {
        return 0.00529393274f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 73.3000031f) {
      if (!isnan(x[66]) && x[66] < 0.5f) {
        return -0.0606377125f;
      } else {
        return 0.273088068f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -0.866025388f) {
        return 0.208714247f;
      } else {
        return -0.0214339551f;
      }
    }
  }
}
static inline float indra_tree_0_3(const float *x) {
  if (!isnan(x[33]) && x[33] < 5.0999999f) {
    if (isnan(x[57]) || x[57] < 6.69999981f) {
      if (!isnan(x[26]) && x[26] < 910.900024f) {
        return 0.0978281349f;
      } else {
        return -0.0717467591f;
      }
    } else {
      if (isnan(x[4]) || x[4] < 35.0f) {
        return 0.00719250878f;
      } else {
        return 0.379296303f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 73.3000031f) {
      if (!isnan(x[15]) && x[15] < 62.0f) {
        return -0.0515446924f;
      } else {
        return 0.210828349f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -0.5f) {
        return 0.0764158741f;
      } else {
        return -0.0501177572f;
      }
    }
  }
}
static inline float indra_tree_0_4(const float *x) {
  if (!isnan(x[32]) && x[32] < 4.9000001f) {
    if (isnan(x[42]) || x[42] < 35.5999985f) {
      if (isnan(x[57]) || x[57] < 8.5f) {
        return -0.0721268207f;
      } else {
        return 0.149336249f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -0.5f) {
        return 0.338566929f;
      } else {
        return -0.00305426936f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 72.7166977f) {
      if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
        return 0.269008815f;
      } else {
        return -0.0747214407f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -0.866025388f) {
        return 0.170401424f;
      } else {
        return -0.00947797485f;
      }
    }
  }
}
static inline float indra_tree_0_5(const float *x) {
  if (!isnan(x[33]) && x[33] < 6.19999981f) {
    if (isnan(x[57]) || x[57] < 7.69999981f) {
      if (isnan(x[4]) || x[4] < 35.0f) {
        return -0.0649545416f;
      } else {
        return 0.030479053f;
      }
    } else {
      if (!isnan(x[62]) && x[62] < 33.4944801f) {
        return -0.0121165542f;
      } else {
        return 0.318518132f;
      }
    }
  } else {
    if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
      if (!isnan(x[70]) && x[70] < 72.7166977f) {
        return 0.218026027f;
      } else {
        return 0.0430658571f;
      }
    } else {
      if (isnan(x[9]) || x[9] < -0.933333337f) {
        return 0.00425031176f;
      } else {
        return -0.0919015631f;
      }
    }
  }
}
static inline float indra_tree_0_6(const float *x) {
  if (!isnan(x[32]) && x[32] < 4.9000001f) {
    if (isnan(x[42]) || x[42] < 35.5999985f) {
      if (isnan(x[57]) || x[57] < 8.5f) {
        return -0.0682999715f;
      } else {
        return 0.116523162f;
      }
    } else {
      if (isnan(x[15]) || x[15] < 39.0f) {
        return -0.0215854477f;
      } else {
        return 0.226453856f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 73.3000031f) {
      if (isnan(x[40]) || x[40] < 1.0f) {
        return 0.0883237273f;
      } else {
        return 0.478639364f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -0.866025388f) {
        return 0.131321937f;
      } else {
        return -0.025397405f;
      }
    }
  }
}
static inline float indra_tree_0_7(const float *x) {
  if (!isnan(x[33]) && x[33] < 5.0999999f) {
    if (isnan(x[8]) || x[8] < 39.0f) {
      if (isnan(x[47]) || x[47] < 5.0999999f) {
        return -0.0616053417f;
      } else {
        return 0.178992525f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 27.2954998f) {
        return 0.00426812423f;
      } else {
        return 0.4134233f;
      }
    }
  } else {
    if (!isnan(x[5]) && x[5] < 31.0f) {
      if (!isnan(x[70]) && x[70] < 73.3000031f) {
        return 0.0397974998f;
      } else {
        return -0.0527280234f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
        return 0.110951863f;
      } else {
        return -0.0435014032f;
      }
    }
  }
}
static inline float indra_tree_0_8(const float *x) {
  if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
    if (isnan(x[5]) || x[5] < 22.5f) {
      if (!isnan(x[67]) && x[67] < -0.866025388f) {
        return 0.226892024f;
      } else {
        return 0.0619870424f;
      }
    } else {
      if (isnan(x[42]) || x[42] < 33.2999992f) {
        return -0.0286147296f;
      } else {
        return 0.110609986f;
      }
    }
  } else {
    if (!isnan(x[28]) && x[28] < 915.5f) {
      if (!isnan(x[5]) && x[5] < 22.5f) {
        return -0.0560539141f;
      } else {
        return 0.240525246f;
      }
    } else {
      if (isnan(x[9]) || x[9] < -1.20000005f) {
        return -0.0468953736f;
      } else {
        return -0.082417272f;
      }
    }
  }
}
static inline float indra_tree_0_9(const float *x) {
  if (isnan(x[34]) || x[34] < 4.4000001f) {
    if (!isnan(x[33]) && x[33] < 5.0999999f) {
      if (isnan(x[37]) || x[37] < 1.85241961f) {
        return -0.0603214875f;
      } else {
        return 0.15868412f;
      }
    } else {
      if (!isnan(x[66]) && x[66] < 1.22464685e-16f) {
        return -0.06894283f;
      } else {
        return 0.0264411662f;
      }
    }
  } else {
    if (!isnan(x[8]) && x[8] < 29.3999996f) {
      if (isnan(x[31]) || x[31] < 0.25f) {
        return 0.708164573f;
      } else {
        return 0.0223949309f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 20.2444f) {
        return -0.0341786593f;
      } else {
        return 0.086132668f;
      }
    }
  }
}
static inline float indra_tree_0_10(const float *x) {
  if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
    if (isnan(x[71]) || x[71] < 225.0f) {
      if (isnan(x[15]) || x[15] < 51.0f) {
        return 0.107679777f;
      } else {
        return -0.00460225763f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 21.0f) {
        return 0.158138201f;
      } else {
        return -0.0501614511f;
      }
    }
  } else {
    if (!isnan(x[28]) && x[28] < 940.5f) {
      if (!isnan(x[5]) && x[5] < 26.5f) {
        return -0.0462465994f;
      } else {
        return 0.236114979f;
      }
    } else {
      if (isnan(x[8]) || x[8] < 25.0f) {
        return -0.0838560984f;
      } else {
        return -0.0437782966f;
      }
    }
  }
}
static inline float indra_tree_0_11(const float *x) {
  if (!isnan(x[32]) && x[32] < 4.9000001f) {
    if (isnan(x[39]) || x[39] < 2.19615245f) {
      if (!isnan(x[69]) && x[69] < 31.7096004f) {
        return -0.0555616803f;
      } else {
        return 0.089345634f;
      }
    } else {
      if (!isnan(x[45]) && x[45] < 51.0f) {
        return 0.432758093f;
      } else {
        return -0.033106491f;
      }
    }
  } else {
    if (isnan(x[46]) || x[46] < 1.10000002f) {
      if (!isnan(x[71]) && x[71] < 225.0f) {
        return 0.0419989787f;
      } else {
        return -0.0474676304f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.5f) {
        return -0.011652695f;
      } else {
        return 0.471199125f;
      }
    }
  }
}
static inline float indra_tree_0_12(const float *x) {
  if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (!isnan(x[69]) && x[69] < 31.7096004f) {
        return -0.0352739543f;
      } else {
        return 0.132595316f;
      }
    } else {
      if (isnan(x[47]) || x[47] < 5.0999999f) {
        return 0.0347970352f;
      } else {
        return 0.379292607f;
      }
    }
  } else {
    if (!isnan(x[28]) && x[28] < 940.5f) {
      if (!isnan(x[5]) && x[5] < 26.5f) {
        return -0.0425065421f;
      } else {
        return 0.19691886f;
      }
    } else {
      if (isnan(x[8]) || x[8] < 25.0f) {
        return -0.0819139108f;
      } else {
        return -0.0396124534f;
      }
    }
  }
}
static inline float indra_tree_0_13(const float *x) {
  if (!isnan(x[33]) && x[33] < 5.0999999f) {
    if (isnan(x[57]) || x[57] < 6.69999981f) {
      if (!isnan(x[26]) && x[26] < 910.900024f) {
        return 0.123153567f;
      } else {
        return -0.0544045232f;
      }
    } else {
      if (!isnan(x[47]) && x[47] < 2.5666666f) {
        return 0.172027484f;
      } else {
        return -0.057726413f;
      }
    }
  } else {
    if (!isnan(x[71]) && x[71] < 225.0f) {
      if (!isnan(x[8]) && x[8] < 29.3999996f) {
        return 0.125568733f;
      } else {
        return 0.0226384532f;
      }
    } else {
      if (!isnan(x[28]) && x[28] < 942.5f) {
        return 0.148607954f;
      } else {
        return -0.0574485324f;
      }
    }
  }
}
static inline float indra_tree_0_14(const float *x) {
  if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
    if (!isnan(x[69]) && x[69] < 14.4499998f) {
      if (isnan(x[8]) || x[8] < 26.0f) {
        return -0.0040599918f;
      } else {
        return -0.0846982822f;
      }
    } else {
      if (isnan(x[71]) || x[71] < 225.0f) {
        return 0.0478621088f;
      } else {
        return -0.0321517996f;
      }
    }
  } else {
    if (!isnan(x[28]) && x[28] < 940.5f) {
      if (isnan(x[34]) || x[34] < 0.5f) {
        return -0.0643732175f;
      } else {
        return 0.135205209f;
      }
    } else {
      if (isnan(x[8]) || x[8] < 25.0f) {
        return -0.07987234f;
      } else {
        return -0.0358824618f;
      }
    }
  }
}
static inline float indra_tree_0_15(const float *x) {
  if (!isnan(x[3]) && x[3] < 2.5999999f) {
    if (isnan(x[57]) || x[57] < 6.69999981f) {
      if (!isnan(x[4]) && x[4] < 30.5f) {
        return -0.0917801112f;
      } else {
        return -0.0296538305f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 2.9755888f) {
        return -0.0319199674f;
      } else {
        return 0.344080657f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[70]) && x[70] < 73.3000031f) {
        return 0.042826619f;
      } else {
        return -0.0270681269f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -0.866025388f) {
        return 0.294911027f;
      } else {
        return 0.0448015109f;
      }
    }
  }
}
static inline float indra_tree_0_16(const float *x) {
  if (!isnan(x[57]) && x[57] < 6.69999981f) {
    if (isnan(x[8]) || x[8] < 37.4000015f) {
      if (!isnan(x[32]) && x[32] < 0.166666672f) {
        return -0.0105226403f;
      } else {
        return -0.0917734653f;
      }
    } else {
      if (!isnan(x[44]) && x[44] < 31.0f) {
        return -0.0421355106f;
      } else {
        return 0.141770527f;
      }
    }
  } else {
    if (isnan(x[42]) || x[42] < 33.2999992f) {
      if (!isnan(x[32]) && x[32] < 4.9000001f) {
        return -0.039242629f;
      } else {
        return 0.0160240848f;
      }
    } else {
      if (isnan(x[15]) || x[15] < 39.0f) {
        return -0.0213202685f;
      } else {
        return 0.175594598f;
      }
    }
  }
}
static inline float indra_tree_0_17(const float *x) {
  if (!isnan(x[57]) && x[57] < 6.69999981f) {
    if (!isnan(x[62]) && x[62] < 42.3154449f) {
      if (isnan(x[40]) || x[40] < 10.6000004f) {
        return -0.0887659341f;
      } else {
        return 0.0377419889f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 59.0f) {
        return 0.1433191f;
      } else {
        return -0.0426592641f;
      }
    }
  } else {
    if (!isnan(x[69]) && x[69] < 31.7096004f) {
      if (!isnan(x[3]) && x[3] < 2.3499999f) {
        return -0.0370589197f;
      } else {
        return 0.0189498533f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 27.0f) {
        return -0.0182509888f;
      } else {
        return 0.2525419f;
      }
    }
  }
}
static inline float indra_tree_0_18(const float *x) {
  if (!isnan(x[69]) && x[69] < 12.9700003f) {
    if (!isnan(x[34]) && x[34] < 0.666666687f) {
      if (!isnan(x[0]) && x[0] < 26.666666f) {
        return 0.100969397f;
      } else {
        return -0.068060644f;
      }
    } else {
      if (isnan(x[37]) || x[37] < 1.10176623f) {
        return -0.0933814347f;
      } else {
        return -0.0223419275f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 85.321701f) {
      if (isnan(x[71]) || x[71] < 225.0f) {
        return 0.0324511193f;
      } else {
        return -0.0291630682f;
      }
    } else {
      if (isnan(x[9]) || x[9] < 1.5f) {
        return -0.0719839856f;
      } else {
        return 0.0354708098f;
      }
    }
  }
}
static inline float indra_tree_0_19(const float *x) {
  if (!isnan(x[57]) && x[57] < 6.69999981f) {
    if (isnan(x[8]) || x[8] < 37.4000015f) {
      if (!isnan(x[32]) && x[32] < 0.166666672f) {
        return -0.00396523066f;
      } else {
        return -0.0899748057f;
      }
    } else {
      if (!isnan(x[44]) && x[44] < 32.0f) {
        return -0.0425026044f;
      } else {
        return 0.135015622f;
      }
    }
  } else {
    if (!isnan(x[53]) && x[53] < 27.0f) {
      if (!isnan(x[15]) && x[15] < 39.0f) {
        return -0.0054618055f;
      } else {
        return 0.325114995f;
      }
    } else {
      if (!isnan(x[3]) && x[3] < 2.5999999f) {
        return -0.0306352917f;
      } else {
        return 0.0151725607f;
      }
    }
  }
}
static inline float indra_tree_0_20(const float *x) {
  if (!isnan(x[69]) && x[69] < 12.9700003f) {
    if (!isnan(x[34]) && x[34] < 0.666666687f) {
      if (!isnan(x[69]) && x[69] < 10.1520004f) {
        return 0.106441222f;
      } else {
        return -0.0673470721f;
      }
    } else {
      if (isnan(x[37]) || x[37] < 1.10176623f) {
        return -0.0924338102f;
      } else {
        return -0.018514704f;
      }
    }
  } else {
    if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
      if (isnan(x[8]) || x[8] < 29.1000004f) {
        return 0.0687554777f;
      } else {
        return -0.000273531768f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 14.4499998f) {
        return 0.0963702723f;
      } else {
        return -0.0437262766f;
      }
    }
  }
}
static inline float indra_tree_0_21(const float *x) {
  if (!isnan(x[64]) && x[64] < 0.707106769f) {
    if (!isnan(x[69]) && x[69] < 31.7096004f) {
      if (!isnan(x[33]) && x[33] < 5.0999999f) {
        return -0.0561061203f;
      } else {
        return -0.00168219337f;
      }
    } else {
      if (isnan(x[50]) || x[50] < 26.5f) {
        return -0.0196010601f;
      } else {
        return 0.250905961f;
      }
    }
  } else {
    if (isnan(x[47]) || x[47] < 5.0999999f) {
      if (!isnan(x[5]) && x[5] < 31.0f) {
        return -0.0321558975f;
      } else {
        return 0.0436632745f;
      }
    } else {
      if (isnan(x[17]) || x[17] < 63.0f) {
        return -0.000698624819f;
      } else {
        return 0.391069949f;
      }
    }
  }
}
static inline float indra_tree_0_22(const float *x) {
  if (!isnan(x[57]) && x[57] < 6.69999981f) {
    if (isnan(x[40]) || x[40] < 6.0f) {
      if (!isnan(x[69]) && x[69] < 26.8999996f) {
        return -0.0914460346f;
      } else {
        return -0.0239149835f;
      }
    } else {
      if (!isnan(x[19]) && x[19] < -1.5f) {
        return -0.0608745813f;
      } else {
        return 0.118716419f;
      }
    }
  } else {
    if (isnan(x[41]) || x[41] < 31.0f) {
      if (!isnan(x[70]) && x[70] < 72.7166977f) {
        return 0.0413251147f;
      } else {
        return -0.0127489744f;
      }
    } else {
      if (!isnan(x[31]) && x[31] < 3.1500001f) {
        return 0.235787064f;
      } else {
        return 0.00771710975f;
      }
    }
  }
}
static inline float indra_tree_0_23(const float *x) {
  if (!isnan(x[66]) && x[66] < 1.22464685e-16f) {
    if (!isnan(x[69]) && x[69] < 17.2332993f) {
      if (!isnan(x[69]) && x[69] < 12.9700003f) {
        return -0.0681242719f;
      } else {
        return 0.0272374749f;
      }
    } else {
      if (!isnan(x[31]) && x[31] < 1.0333333f) {
        return -0.0101978444f;
      } else {
        return -0.0881104767f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (!isnan(x[69]) && x[69] < 28.0f) {
        return -0.0361880809f;
      } else {
        return 0.0515720956f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 21.6166992f) {
        return -0.0014700708f;
      } else {
        return 0.0715285018f;
      }
    }
  }
}
static inline float indra_tree_0_24(const float *x) {
  if (!isnan(x[57]) && x[57] < 6.69999981f) {
    if (isnan(x[40]) || x[40] < 6.0f) {
      if (!isnan(x[69]) && x[69] < 26.8999996f) {
        return -0.0903135762f;
      } else {
        return -0.0238734428f;
      }
    } else {
      if (!isnan(x[19]) && x[19] < -1.5f) {
        return -0.0595051646f;
      } else {
        return 0.100082956f;
      }
    }
  } else {
    if (!isnan(x[66]) && x[66] < 1.22464685e-16f) {
      if (!isnan(x[69]) && x[69] < 17.2332993f) {
        return 0.00794705655f;
      } else {
        return -0.064461939f;
      }
    } else {
      if (!isnan(x[3]) && x[3] < 6.19999981f) {
        return 0.0425390564f;
      } else {
        return -0.0121950163f;
      }
    }
  }
}
static inline float indra_tree_0_25(const float *x) {
  if (!isnan(x[69]) && x[69] < 12.9700003f) {
    if (!isnan(x[34]) && x[34] < 0.666666687f) {
      if (!isnan(x[8]) && x[8] < 26.7000008f) {
        return 0.113105893f;
      } else {
        return -0.0640596002f;
      }
    } else {
      if (isnan(x[37]) || x[37] < 1.10176623f) {
        return -0.0906068236f;
      } else {
        return -0.00940707047f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 85.321701f) {
      if (isnan(x[17]) || x[17] < 83.0f) {
        return 0.00120260369f;
      } else {
        return 0.0749775842f;
      }
    } else {
      if (isnan(x[9]) || x[9] < 1.5f) {
        return -0.0675841495f;
      } else {
        return 0.0340809301f;
      }
    }
  }
}
static inline float indra_tree_0_26(const float *x) {
  if (!isnan(x[10]) && x[10] < 26.666666f) {
    if (isnan(x[56]) || x[56] < 3.8499999f) {
      if (!isnan(x[1]) && x[1] < 97.0f) {
        return -0.0898777544f;
      } else {
        return -0.000623761851f;
      }
    } else {
      return 0.0939824209f;
    }
  } else {
    if (!isnan(x[69]) && x[69] < 31.7096004f) {
      if (isnan(x[34]) || x[34] < 2.04999995f) {
        return -0.0287561845f;
      } else {
        return 0.0127239525f;
      }
    } else {
      if (!isnan(x[33]) && x[33] < 2.3499999f) {
        return 0.00967606809f;
      } else {
        return 0.196663201f;
      }
    }
  }
}
static inline float indra_tree_0_27(const float *x) {
  if (!isnan(x[4]) && x[4] < 26.5f) {
    if (isnan(x[46]) || x[46] < 2.8499999f) {
      if (isnan(x[44]) || x[44] < 94.0f) {
        return -0.0764264688f;
      } else {
        return 0.0589888059f;
      }
    } else {
      return 0.141507313f;
    }
  } else {
    if (!isnan(x[8]) && x[8] < 29.1000004f) {
      if (!isnan(x[3]) && x[3] < 5.0999999f) {
        return 0.0086681461f;
      } else {
        return 0.283642739f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 21.6166992f) {
        return -0.0358125679f;
      } else {
        return 0.0315620005f;
      }
    }
  }
}
static inline float indra_tree_0_28(const float *x) {
  if (!isnan(x[69]) && x[69] < 12.9499998f) {
    if (!isnan(x[34]) && x[34] < 0.666666687f) {
      if (!isnan(x[0]) && x[0] < 26.666666f) {
        return 0.110551417f;
      } else {
        return -0.061798688f;
      }
    } else {
      if (isnan(x[25]) || x[25] < 1007.5f) {
        return -0.0944490433f;
      } else {
        return -0.00355758565f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 85.321701f) {
      if (isnan(x[71]) || x[71] < 225.0f) {
        return 0.0238260049f;
      } else {
        return -0.0243810862f;
      }
    } else {
      if (isnan(x[9]) || x[9] < 1.5f) {
        return -0.0648283288f;
      } else {
        return 0.0342285037f;
      }
    }
  }
}
static inline float indra_tree_0_29(const float *x) {
  if (!isnan(x[57]) && x[57] < 6.69999981f) {
    if (isnan(x[40]) || x[40] < 6.0f) {
      if (!isnan(x[11]) && x[11] < 0.343592137f) {
        return -0.00052040827f;
      } else {
        return -0.0846068859f;
      }
    } else {
      if (!isnan(x[11]) && x[11] < 1.88561809f) {
        return 0.139379218f;
      } else {
        return -0.0363914855f;
      }
    }
  } else {
    if (!isnan(x[66]) && x[66] < -0.5f) {
      if (!isnan(x[26]) && x[26] < 943.900024f) {
        return 0.09804672f;
      } else {
        return -0.0725017935f;
      }
    } else {
      if (!isnan(x[3]) && x[3] < 6.19999981f) {
        return 0.0297304597f;
      } else {
        return -0.0124187693f;
      }
    }
  }
}
static inline float indra_tree_0_30(const float *x) {
  if (isnan(x[34]) || x[34] < 4.4000001f) {
    if (!isnan(x[3]) && x[3] < 6.19999981f) {
      if (!isnan(x[3]) && x[3] < 2.5999999f) {
        return -0.0287874769f;
      } else {
        return 0.0413858108f;
      }
    } else {
      if (!isnan(x[8]) && x[8] < 29.0f) {
        return 0.142061815f;
      } else {
        return -0.0717371851f;
      }
    }
  } else {
    if (!isnan(x[8]) && x[8] < 29.3999996f) {
      if (!isnan(x[70]) && x[70] < 78.75f) {
        return 0.0225751679f;
      } else {
        return 0.419397503f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 20.2444f) {
        return -0.0383862406f;
      } else {
        return 0.0363740139f;
      }
    }
  }
}
static inline float indra_tree_0_31(const float *x) {
  if (!isnan(x[10]) && x[10] < 26.666666f) {
    if (isnan(x[56]) || x[56] < 4.0999999f) {
      if (isnan(x[14]) || x[14] < 97.0f) {
        return -0.0884620622f;
      } else {
        return -0.000269793789f;
      }
    } else {
      return 0.0912995115f;
    }
  } else {
    if (!isnan(x[65]) && x[65] < -0.707106769f) {
      if (!isnan(x[50]) && x[50] < 21.1000004f) {
        return 0.167125657f;
      } else {
        return -0.0445854217f;
      }
    } else {
      if (isnan(x[15]) || x[15] < 72.0f) {
        return 0.0259341132f;
      } else {
        return -0.0197627172f;
      }
    }
  }
}
static inline float indra_tree_0_32(const float *x) {
  if (!isnan(x[67]) && x[67] < 0.5f) {
    if (isnan(x[2]) || x[2] < 942.5f) {
      if (isnan(x[15]) || x[15] < 72.0f) {
        return 0.0263250303f;
      } else {
        return -0.0190350749f;
      }
    } else {
      if (!isnan(x[5]) && x[5] < 25.0666676f) {
        return 0.130493999f;
      } else {
        return -0.0850616321f;
      }
    }
  } else {
    if (!isnan(x[59]) && x[59] < 19.9565105f) {
      if (!isnan(x[0]) && x[0] < 16.5f) {
        return 0.0196962059f;
      } else {
        return -0.0801238492f;
      }
    } else {
      if (!isnan(x[70]) && x[70] < 74.8799973f) {
        return 0.362158477f;
      } else {
        return -0.0363599621f;
      }
    }
  }
}
static inline float indra_tree_0_33(const float *x) {
  if (!isnan(x[57]) && x[57] < 6.69999981f) {
    if (isnan(x[40]) || x[40] < 6.0f) {
      if (!isnan(x[35]) && x[35] < 0.5f) {
        return -0.0924637243f;
      } else {
        return -0.0352502428f;
      }
    } else {
      if (!isnan(x[11]) && x[11] < 1.82574189f) {
        return 0.138523191f;
      } else {
        return -0.0362488702f;
      }
    }
  } else {
    if (!isnan(x[3]) && x[3] < 6.19999981f) {
      if (!isnan(x[3]) && x[3] < 2.5999999f) {
        return -0.017614603f;
      } else {
        return 0.0678752884f;
      }
    } else {
      if (!isnan(x[8]) && x[8] < 29.1000004f) {
        return 0.152034447f;
      } else {
        return -0.0295246821f;
      }
    }
  }
}
static inline float indra_tree_0_34(const float *x) {
  if (!isnan(x[4]) && x[4] < 26.5f) {
    if (isnan(x[46]) || x[46] < 2.8499999f) {
      if (isnan(x[44]) || x[44] < 94.0f) {
        return -0.0733734891f;
      } else {
        return 0.0614984222f;
      }
    } else {
      return 0.119640268f;
    }
  } else {
    if (!isnan(x[8]) && x[8] < 29.1000004f) {
      if (isnan(x[34]) || x[34] < 5.4000001f) {
        return 0.0134095047f;
      } else {
        return 0.183345929f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 21.6166992f) {
        return -0.0306113865f;
      } else {
        return 0.025080068f;
      }
    }
  }
}
static inline float indra_tree_0_35(const float *x) {
  if (!isnan(x[64]) && x[64] < 0.707106769f) {
    if (!isnan(x[63]) && x[63] < 23.935133f) {
      if (isnan(x[23]) || x[23] < 19.4834328f) {
        return -0.0387645327f;
      } else {
        return 0.119855739f;
      }
    } else {
      if (!isnan(x[62]) && x[62] < 32.0113029f) {
        return 0.296403021f;
      } else {
        return 0.0101937484f;
      }
    }
  } else {
    if (isnan(x[47]) || x[47] < 5.0999999f) {
      if (!isnan(x[5]) && x[5] < 30.5f) {
        return -0.0273931772f;
      } else {
        return 0.028520925f;
      }
    } else {
      if (!isnan(x[54]) && x[54] < 92.5f) {
        return -0.0633898601f;
      } else {
        return 0.239834383f;
      }
    }
  }
}
static inline float indra_tree_0_36(const float *x) {
  if (!isnan(x[42]) && x[42] < 33.2999992f) {
    if (isnan(x[32]) || x[32] < 4.13333321f) {
      if (isnan(x[23]) || x[23] < 19.4834328f) {
        return -0.0741575733f;
      } else {
        return 0.0640301332f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.5f) {
        return -0.0635652989f;
      } else {
        return 0.0903028622f;
      }
    }
  } else {
    if (isnan(x[44]) || x[44] < 37.0f) {
      if (!isnan(x[65]) && x[65] < -0.5f) {
        return -0.0485880636f;
      } else {
        return 0.010384148f;
      }
    } else {
      if (isnan(x[53]) || x[53] < 40.0f) {
        return 0.108116522f;
      } else {
        return -0.0506769791f;
      }
    }
  }
}
static inline float indra_tree_0_37(const float *x) {
  if (!isnan(x[70]) && x[70] < 85.321701f) {
    if (!isnan(x[70]) && x[70] < 81.8184967f) {
      if (!isnan(x[30]) && x[30] < 6.69999981f) {
        return -0.0330864638f;
      } else {
        return 0.0155778183f;
      }
    } else {
      if (isnan(x[16]) || x[16] < 46.5f) {
        return 0.162871674f;
      } else {
        return -0.0234627873f;
      }
    }
  } else {
    if (isnan(x[9]) || x[9] < 1.5f) {
      if (!isnan(x[69]) && x[69] < 28.0f) {
        return -0.0715594292f;
      } else {
        return 0.058842998f;
      }
    } else {
      if (!isnan(x[18]) && x[18] < 56.5f) {
        return 0.148640469f;
      } else {
        return -0.0499823056f;
      }
    }
  }
}
static inline float indra_tree_0_38(const float *x) {
  if (!isnan(x[69]) && x[69] < 12.9499998f) {
    if (!isnan(x[34]) && x[34] < 0.666666687f) {
      if (!isnan(x[69]) && x[69] < 10.1520004f) {
        return 0.123708084f;
      } else {
        return -0.0588387623f;
      }
    } else {
      if (isnan(x[2]) || x[2] < 1007.40002f) {
        return -0.0925592929f;
      } else {
        return -0.00148977654f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 85.321701f) {
      if (isnan(x[17]) || x[17] < 83.0f) {
        return -0.000378526689f;
      } else {
        return 0.0596756712f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.866025388f) {
        return -0.0795888975f;
      } else {
        return -0.00791046396f;
      }
    }
  }
}
static inline float indra_tree_0_39(const float *x) {
  if (!isnan(x[10]) && x[10] < 26.666666f) {
    if (isnan(x[56]) || x[56] < 4.0999999f) {
      if (isnan(x[16]) || x[16] < 94.0f) {
        return -0.0913966671f;
      } else {
        return -0.02747727f;
      }
    } else {
      return 0.0635107905f;
    }
  } else {
    if (!isnan(x[69]) && x[69] < 31.7096004f) {
      if (!isnan(x[15]) && x[15] < 39.0f) {
        return -0.0569297448f;
      } else {
        return 0.00401265686f;
      }
    } else {
      if (!isnan(x[33]) && x[33] < 1.56666672f) {
        return -0.0175871681f;
      } else {
        return 0.130102828f;
      }
    }
  }
}
static inline float indra_raw_0(const float *x) {
  float margin=-7.2502207f;
  margin+=indra_tree_0_0(x);
  margin+=indra_tree_0_1(x);
  margin+=indra_tree_0_2(x);
  margin+=indra_tree_0_3(x);
  margin+=indra_tree_0_4(x);
  margin+=indra_tree_0_5(x);
  margin+=indra_tree_0_6(x);
  margin+=indra_tree_0_7(x);
  margin+=indra_tree_0_8(x);
  margin+=indra_tree_0_9(x);
  margin+=indra_tree_0_10(x);
  margin+=indra_tree_0_11(x);
  margin+=indra_tree_0_12(x);
  margin+=indra_tree_0_13(x);
  margin+=indra_tree_0_14(x);
  margin+=indra_tree_0_15(x);
  margin+=indra_tree_0_16(x);
  margin+=indra_tree_0_17(x);
  margin+=indra_tree_0_18(x);
  margin+=indra_tree_0_19(x);
  margin+=indra_tree_0_20(x);
  margin+=indra_tree_0_21(x);
  margin+=indra_tree_0_22(x);
  margin+=indra_tree_0_23(x);
  margin+=indra_tree_0_24(x);
  margin+=indra_tree_0_25(x);
  margin+=indra_tree_0_26(x);
  margin+=indra_tree_0_27(x);
  margin+=indra_tree_0_28(x);
  margin+=indra_tree_0_29(x);
  margin+=indra_tree_0_30(x);
  margin+=indra_tree_0_31(x);
  margin+=indra_tree_0_32(x);
  margin+=indra_tree_0_33(x);
  margin+=indra_tree_0_34(x);
  margin+=indra_tree_0_35(x);
  margin+=indra_tree_0_36(x);
  margin+=indra_tree_0_37(x);
  margin+=indra_tree_0_38(x);
  margin+=indra_tree_0_39(x);
  return 1.0f/(1.0f+expf(-margin));
}
static inline float indra_tree_1_0(const float *x) {
  if (!isnan(x[7]) && x[7] < 29.0f) {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (!isnan(x[0]) && x[0] < 39.0f) {
        return -0.10793332f;
      } else {
        return -0.0163606182f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 3.68341851f) {
        return -0.0514002517f;
      } else {
        return 0.387904763f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.258819044f) {
      if (isnan(x[12]) || x[12] < 36.1854172f) {
        return -0.0883883163f;
      } else {
        return 0.422238171f;
      }
    } else {
      if (isnan(x[7]) || x[7] < 31.5f) {
        return 0.0917828605f;
      } else {
        return 0.656504512f;
      }
    }
  }
}
static inline float indra_tree_1_1(const float *x) {
  if (!isnan(x[66]) && x[66] < 0.5f) {
    if (!isnan(x[62]) && x[62] < 31.3465652f) {
      if (!isnan(x[66]) && x[66] < -0.866025388f) {
        return -0.075599432f;
      } else {
        return -0.105197147f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.0827325284f;
      } else {
        return 0.0547522269f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (isnan(x[7]) || x[7] < 35.2000008f) {
        return -0.06321273f;
      } else {
        return 0.182248428f;
      }
    } else {
      if (isnan(x[7]) || x[7] < 29.1000004f) {
        return 0.106322825f;
      } else {
        return 0.511762977f;
      }
    }
  }
}
static inline float indra_tree_1_2(const float *x) {
  if (!isnan(x[7]) && x[7] < 28.5f) {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (isnan(x[9]) || x[9] < 1.5f) {
        return -0.104713164f;
      } else {
        return -0.0441104136f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 3.40432644f) {
        return -0.056240011f;
      } else {
        return 0.270631164f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[61]) && x[61] < 5.29980612f) {
        return -0.094441846f;
      } else {
        return 0.363144487f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 62.0f) {
        return 0.297665209f;
      } else {
        return 0.0495770946f;
      }
    }
  }
}
static inline float indra_tree_1_3(const float *x) {
  if (!isnan(x[0]) && x[0] < 29.1000004f) {
    if (!isnan(x[66]) && x[66] < 0.866025388f) {
      if (isnan(x[7]) || x[7] < 36.0f) {
        return -0.0906435028f;
      } else {
        return 0.0935952812f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.0f) {
        return -0.10115619f;
      } else {
        return 0.0812614188f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < -0.258819044f) {
      if (!isnan(x[0]) && x[0] < 39.0f) {
        return -0.0962511823f;
      } else {
        return 0.256042242f;
      }
    } else {
      if (isnan(x[15]) || x[15] < 67.0f) {
        return 0.30789867f;
      } else {
        return 0.092210643f;
      }
    }
  }
}
static inline float indra_tree_1_4(const float *x) {
  if (!isnan(x[67]) && x[67] < 0.5f) {
    if (!isnan(x[64]) && x[64] < 0.258819044f) {
      if (isnan(x[7]) || x[7] < 39.2000008f) {
        return -0.0902040452f;
      } else {
        return 0.0899588764f;
      }
    } else {
      if (!isnan(x[66]) && x[66] < 0.5f) {
        return -0.0343096592f;
      } else {
        return 0.169288203f;
      }
    }
  } else {
    if (!isnan(x[66]) && x[66] < 0.866025388f) {
      if (isnan(x[51]) || x[51] < 35.5f) {
        return -0.100982986f;
      } else {
        return -0.00253297715f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return -0.0903206095f;
      } else {
        return 0.025620237f;
      }
    }
  }
}
static inline float indra_tree_1_5(const float *x) {
  if (!isnan(x[67]) && x[67] < 0.5f) {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[0]) && x[0] < 39.0f) {
        return -0.0921965241f;
      } else {
        return 0.133260593f;
      }
    } else {
      if (isnan(x[16]) || x[16] < 72.0f) {
        return 0.151693732f;
      } else {
        return -0.00746878842f;
      }
    }
  } else {
    if (!isnan(x[66]) && x[66] < 0.866025388f) {
      if (isnan(x[51]) || x[51] < 35.5f) {
        return -0.0995982513f;
      } else {
        return -0.00228753546f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return -0.0879701599f;
      } else {
        return 0.0225975495f;
      }
    }
  }
}
static inline float indra_tree_1_6(const float *x) {
  if (!isnan(x[7]) && x[7] < 28.0f) {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (isnan(x[9]) || x[9] < 1.5f) {
        return -0.102865435f;
      } else {
        return -0.0606345311f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 33.0f) {
        return -0.0653868392f;
      } else {
        return 0.0965427384f;
      }
    }
  } else {
    if (!isnan(x[61]) && x[61] < 1.13397908f) {
      if (!isnan(x[64]) && x[64] < 0.258819044f) {
        return -0.100297391f;
      } else {
        return -0.007590733f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return 0.0398990586f;
      } else {
        return 0.217668369f;
      }
    }
  }
}
static inline float indra_tree_1_7(const float *x) {
  if (!isnan(x[0]) && x[0] < 28.2000008f) {
    if (!isnan(x[66]) && x[66] < 0.866025388f) {
      if (isnan(x[7]) || x[7] < 36.0f) {
        return -0.0898288637f;
      } else {
        return 0.04662342f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.103334181f;
      } else {
        return 0.0329878367f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < -0.258819044f) {
      if (!isnan(x[0]) && x[0] < 39.0f) {
        return -0.0955893323f;
      } else {
        return 0.142343014f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0797425136f;
      } else {
        return 0.139234617f;
      }
    }
  }
}
static inline float indra_tree_1_8(const float *x) {
  if (!isnan(x[66]) && x[66] < 0.5f) {
    if (isnan(x[7]) || x[7] < 29.5f) {
      if (!isnan(x[67]) && x[67] < 6.12323426e-17f) {
        return -0.0740381628f;
      } else {
        return -0.102873802f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return -0.0781361759f;
      } else {
        return 0.176424518f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (isnan(x[7]) || x[7] < 39.2000008f) {
        return -0.0920702145f;
      } else {
        return 0.0404261649f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < 0.5f) {
        return 0.100131206f;
      } else {
        return -0.0335944593f;
      }
    }
  }
}
static inline float indra_tree_1_9(const float *x) {
  if (!isnan(x[7]) && x[7] < 27.5f) {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (isnan(x[9]) || x[9] < 1.5f) {
        return -0.101832189f;
      } else {
        return -0.0638784692f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 25.0666676f) {
        return -0.0879750773f;
      } else {
        return 0.000664232648f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (isnan(x[7]) || x[7] < 39.2000008f) {
        return -0.100409225f;
      } else {
        return -0.00176153053f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 66.0f) {
        return 0.122848503f;
      } else {
        return 0.00836033281f;
      }
    }
  }
}
static inline float indra_tree_1_10(const float *x) {
  if (!isnan(x[0]) && x[0] < 27.2000008f) {
    if (!isnan(x[66]) && x[66] < 0.866025388f) {
      if (isnan(x[51]) || x[51] < 36.0f) {
        return -0.0904568359f;
      } else {
        return 0.0545054041f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 23.5f) {
        return -0.0777962729f;
      } else {
        return 0.0180823058f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 6.12323426e-17f) {
      if (!isnan(x[0]) && x[0] < 35.2000008f) {
        return -0.0800726935f;
      } else {
        return 0.0960117355f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0753796324f;
      } else {
        return 0.137805387f;
      }
    }
  }
}
static inline float indra_tree_1_11(const float *x) {
  if (!isnan(x[66]) && x[66] < 0.5f) {
    if (!isnan(x[62]) && x[62] < 31.3465652f) {
      if (!isnan(x[66]) && x[66] < -0.866025388f) {
        return -0.0562298894f;
      } else {
        return -0.0972428694f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.0706861541f;
      } else {
        return 0.0285987593f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.258819044f) {
      if (isnan(x[7]) || x[7] < 37.5f) {
        return -0.0852637738f;
      } else {
        return 0.032524962f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 25.0666676f) {
        return -0.0493062623f;
      } else {
        return 0.0725079849f;
      }
    }
  }
}
static inline float indra_tree_1_12(const float *x) {
  if (!isnan(x[7]) && x[7] < 27.2000008f) {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (isnan(x[9]) || x[9] < 1.5f) {
        return -0.1005136f;
      } else {
        return -0.0575286262f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 24.0499992f) {
        return -0.0948819444f;
      } else {
        return -0.0152582973f;
      }
    }
  } else {
    if (!isnan(x[61]) && x[61] < 0.998502851f) {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.102659643f;
      } else {
        return -0.0223586932f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return 0.01455383f;
      } else {
        return 0.127927929f;
      }
    }
  }
}
static inline float indra_tree_1_13(const float *x) {
  if (!isnan(x[62]) && x[62] < 26.5f) {
    if (isnan(x[7]) || x[7] < 36.0f) {
      if (!isnan(x[66]) && x[66] < 0.866025388f) {
        return -0.0898261443f;
      } else {
        return -0.0428468212f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.103485301f;
      } else {
        return 0.12560831f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < -0.258819044f) {
      if (!isnan(x[0]) && x[0] < 39.0f) {
        return -0.0941691697f;
      } else {
        return 0.0836407542f;
      }
    } else {
      if (!isnan(x[71]) && x[71] < 43.0f) {
        return -0.0196751896f;
      } else {
        return 0.0901515633f;
      }
    }
  }
}
static inline float indra_tree_1_14(const float *x) {
  if (!isnan(x[66]) && x[66] < 0.5f) {
    if (!isnan(x[67]) && x[67] < 6.12323426e-17f) {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return -0.0803934038f;
      } else {
        return -0.0160049163f;
      }
    } else {
      if (!isnan(x[70]) && x[70] < 74.6166992f) {
        return -0.0841200128f;
      } else {
        return -0.102227464f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (isnan(x[8]) || x[8] < 39.0f) {
        return -0.0819042325f;
      } else {
        return 0.0913955048f;
      }
    } else {
      if (isnan(x[16]) || x[16] < 67.0f) {
        return 0.0717935339f;
      } else {
        return -0.0135238189f;
      }
    }
  }
}
static inline float indra_tree_1_15(const float *x) {
  if (!isnan(x[7]) && x[7] < 27.0f) {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (isnan(x[9]) || x[9] < 0.850000024f) {
        return -0.100804761f;
      } else {
        return -0.0757577121f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 33.5f) {
        return -0.0689991266f;
      } else {
        return 0.059686549f;
      }
    }
  } else {
    if (!isnan(x[61]) && x[61] < 2.40340662f) {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.0751123503f;
      } else {
        return 0.0283613391f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return -0.00846383721f;
      } else {
        return 0.133804366f;
      }
    }
  }
}
static inline float indra_tree_1_16(const float *x) {
  if (!isnan(x[67]) && x[67] < 0.5f) {
    if (!isnan(x[1]) && x[1] < 63.0f) {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return -0.0228940193f;
      } else {
        return 0.0943552181f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.0852187499f;
      } else {
        return 0.0165793616f;
      }
    }
  } else {
    if (!isnan(x[66]) && x[66] < 0.866025388f) {
      if (isnan(x[51]) || x[51] < 35.5f) {
        return -0.090234831f;
      } else {
        return 0.0289199259f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.5f) {
        return -0.0904712901f;
      } else {
        return 0.0035189637f;
      }
    }
  }
}
static inline float indra_tree_1_17(const float *x) {
  if (!isnan(x[64]) && x[64] < 0.258819044f) {
    if (isnan(x[51]) || x[51] < 38.5f) {
      if (!isnan(x[61]) && x[61] < 5.29980612f) {
        return -0.091714941f;
      } else {
        return 0.0874952823f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.866025388f) {
        return -0.0450673364f;
      } else {
        return 0.150290728f;
      }
    }
  } else {
    if (isnan(x[7]) || x[7] < 30.5f) {
      if (isnan(x[16]) || x[16] < 72.0f) {
        return 0.0199156385f;
      } else {
        return -0.0562259369f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.965925813f) {
        return 0.118193828f;
      } else {
        return 0.0236158911f;
      }
    }
  }
}
static inline float indra_tree_1_18(const float *x) {
  if (!isnan(x[62]) && x[62] < 26.2000008f) {
    if (isnan(x[7]) || x[7] < 36.0f) {
      if (!isnan(x[64]) && x[64] < 0.5f) {
        return -0.0927476808f;
      } else {
        return -0.0453685448f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.101840533f;
      } else {
        return 0.0931084752f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 6.12323426e-17f) {
      if (!isnan(x[0]) && x[0] < 34.5f) {
        return -0.0838227496f;
      } else {
        return 0.0504056998f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.077204071f;
      } else {
        return 0.0781778991f;
      }
    }
  }
}
static inline float indra_tree_1_19(const float *x) {
  if (!isnan(x[51]) && x[51] < 34.5999985f) {
    if (!isnan(x[51]) && x[51] < 33.5499992f) {
      if (!isnan(x[71]) && x[71] < 43.0f) {
        return -0.108248375f;
      } else {
        return -0.0966971368f;
      }
    } else {
      if (!isnan(x[9]) && x[9] < 3.0f) {
        return -0.0744466558f;
      } else {
        return 0.140586957f;
      }
    }
  } else {
    if (!isnan(x[0]) && x[0] < 25.0f) {
      if (isnan(x[7]) || x[7] < 25.6000004f) {
        return -0.0911964029f;
      } else {
        return -0.0323959179f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 6.12323426e-17f) {
        return -0.020071676f;
      } else {
        return 0.0600202642f;
      }
    }
  }
}
static inline float indra_tree_1_20(const float *x) {
  if (!isnan(x[51]) && x[51] < 34.5999985f) {
    if (!isnan(x[51]) && x[51] < 33.5f) {
      if (isnan(x[49]) || x[49] < 3.0f) {
        return -0.101881802f;
      } else {
        return -0.0766709074f;
      }
    } else {
      if (!isnan(x[9]) && x[9] < 1.5f) {
        return -0.0880579129f;
      } else {
        return -0.0146845123f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[0]) && x[0] < 39.0f) {
        return -0.0813114941f;
      } else {
        return 0.0662459955f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 72.0f) {
        return 0.062879324f;
      } else {
        return -0.00689302385f;
      }
    }
  }
}
static inline float indra_tree_1_21(const float *x) {
  if (!isnan(x[0]) && x[0] < 28.0f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (isnan(x[9]) || x[9] < 3.0f) {
        return -0.102774121f;
      } else {
        return -0.076182358f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 0.83434546f) {
        return -0.0584297851f;
      } else {
        return 0.0388733f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < -0.258819044f) {
      if (!isnan(x[0]) && x[0] < 37.4000015f) {
        return -0.0959670916f;
      } else {
        return 0.0370584801f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 33.5f) {
        return 0.0225482415f;
      } else {
        return 0.114270054f;
      }
    }
  }
}
static inline float indra_tree_1_22(const float *x) {
  if (!isnan(x[7]) && x[7] < 26.0499992f) {
    if (!isnan(x[7]) && x[7] < 24.0499992f) {
      if (!isnan(x[7]) && x[7] < 23.0f) {
        return -0.100493483f;
      } else {
        return -0.0848991498f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return -0.0963298753f;
      } else {
        return -0.0287334453f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (!isnan(x[0]) && x[0] < 32.7999992f) {
        return -0.0958800092f;
      } else {
        return 0.00193402439f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 69.0f) {
        return 0.0590031259f;
      } else {
        return -0.00428566709f;
      }
    }
  }
}
static inline float indra_tree_1_23(const float *x) {
  if (!isnan(x[51]) && x[51] < 34.5999985f) {
    if (!isnan(x[51]) && x[51] < 33.5f) {
      if (isnan(x[49]) || x[49] < 3.0f) {
        return -0.100769661f;
      } else {
        return -0.0715511218f;
      }
    } else {
      if (!isnan(x[5]) && x[5] < 25.6000004f) {
        return -0.00920621678f;
      } else {
        return -0.0850597918f;
      }
    }
  } else {
    if (!isnan(x[62]) && x[62] < 26.0f) {
      if (isnan(x[7]) || x[7] < 25.5f) {
        return -0.0821898356f;
      } else {
        return -0.0236871559f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.258819044f) {
        return -0.0137668727f;
      } else {
        return 0.060161978f;
      }
    }
  }
}
static inline float indra_tree_1_24(const float *x) {
  if (!isnan(x[0]) && x[0] < 31.2000008f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[65]) && x[65] < 0.258819044f) {
        return -0.101203538f;
      } else {
        return -0.0462239198f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 0.91373986f) {
        return -0.0335433446f;
      } else {
        return 0.0550011806f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < -0.258819044f) {
      if (isnan(x[7]) || x[7] < 31.0f) {
        return -0.0637855232f;
      } else {
        return 0.0949757025f;
      }
    } else {
      if (!isnan(x[71]) && x[71] < 43.0f) {
        return -0.0132774785f;
      } else {
        return 0.103316903f;
      }
    }
  }
}
static inline float indra_tree_1_25(const float *x) {
  if (!isnan(x[64]) && x[64] < 0.5f) {
    if (isnan(x[7]) || x[7] < 33.5f) {
      if (isnan(x[8]) || x[8] < 39.0f) {
        return -0.0861832201f;
      } else {
        return 0.0162771773f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0654650256f;
      } else {
        return 0.0530332103f;
      }
    }
  } else {
    if (isnan(x[7]) || x[7] < 30.3999996f) {
      if (isnan(x[16]) || x[16] < 72.0f) {
        return 0.0233842414f;
      } else {
        return -0.0430328436f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 10.1520004f) {
        return -0.118813746f;
      } else {
        return 0.0912083909f;
      }
    }
  }
}
static inline float indra_tree_1_26(const float *x) {
  if (!isnan(x[66]) && x[66] < 0.5f) {
    if (!isnan(x[67]) && x[67] < 6.12323426e-17f) {
      if (isnan(x[71]) || x[71] < 510.0f) {
        return -0.02166011f;
      } else {
        return -0.101691045f;
      }
    } else {
      if (!isnan(x[70]) && x[70] < 74.6166992f) {
        return -0.0676935539f;
      } else {
        return -0.0993076637f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (isnan(x[7]) || x[7] < 33.0f) {
        return -0.0535463169f;
      } else {
        return 0.0194217265f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 35.2000008f) {
        return 0.0198325571f;
      } else {
        return 0.106078856f;
      }
    }
  }
}
static inline float indra_tree_1_27(const float *x) {
  if (!isnan(x[51]) && x[51] < 34.2000008f) {
    if (!isnan(x[9]) && x[9] < 1.60000002f) {
      if (!isnan(x[59]) && x[59] < 26.7541733f) {
        return -0.097480759f;
      } else {
        return -0.0430439971f;
      }
    } else {
      if (!isnan(x[51]) && x[51] < 33.5f) {
        return -0.0802305192f;
      } else {
        return -0.0189816765f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (!isnan(x[0]) && x[0] < 32.7999992f) {
        return -0.0938776061f;
      } else {
        return -0.00337055814f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.258819044f) {
        return -0.0163829606f;
      } else {
        return 0.0395970829f;
      }
    }
  }
}
static inline float indra_tree_1_28(const float *x) {
  if (!isnan(x[0]) && x[0] < 28.5f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (isnan(x[9]) || x[9] < 3.0f) {
        return -0.0999829695f;
      } else {
        return -0.0639382154f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 0.83434546f) {
        return -0.0467978753f;
      } else {
        return 0.0284097921f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.258819044f) {
      if (!isnan(x[0]) && x[0] < 33.5f) {
        return -0.0728752241f;
      } else {
        return 0.0335615687f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.5f) {
        return -0.0959037617f;
      } else {
        return 0.0740314648f;
      }
    }
  }
}
static inline float indra_tree_1_29(const float *x) {
  if (!isnan(x[0]) && x[0] < 23.5f) {
    if (isnan(x[51]) || x[51] < 36.0999985f) {
      if (!isnan(x[0]) && x[0] < 20.5f) {
        return -0.0953019261f;
      } else {
        return -0.0597961545f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.5f) {
        return 0.0489165373f;
      } else {
        return 0.192941442f;
      }
    }
  } else {
    if (!isnan(x[71]) && x[71] < 43.0f) {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.0712344423f;
      } else {
        return -0.0100603467f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return -0.0335090198f;
      } else {
        return 0.0381652899f;
      }
    }
  }
}
static inline float indra_tree_1_30(const float *x) {
  if (!isnan(x[0]) && x[0] < 30.5f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[65]) && x[65] < 0.258819044f) {
        return -0.101636045f;
      } else {
        return -0.0594315603f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 0.762733817f) {
        return -0.0361315124f;
      } else {
        return 0.0290471055f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 6.12323426e-17f) {
      if (!isnan(x[0]) && x[0] < 35.2000008f) {
        return -0.050090827f;
      } else {
        return 0.044269681f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.707106769f) {
        return -0.10284102f;
      } else {
        return 0.0855736062f;
      }
    }
  }
}
static inline float indra_tree_1_31(const float *x) {
  if (!isnan(x[64]) && x[64] < 0.5f) {
    if (isnan(x[7]) || x[7] < 34.0f) {
      if (isnan(x[8]) || x[8] < 39.0f) {
        return -0.0777337402f;
      } else {
        return 0.0213388167f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0584149174f;
      } else {
        return 0.0409940891f;
      }
    }
  } else {
    if (!isnan(x[17]) && x[17] < 69.0f) {
      if (!isnan(x[7]) && x[7] < 25.0666676f) {
        return -0.063520506f;
      } else {
        return 0.071145393f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.258819044f) {
        return -0.0339937583f;
      } else {
        return 0.0235880855f;
      }
    }
  }
}
static inline float indra_tree_1_32(const float *x) {
  if (!isnan(x[51]) && x[51] < 34.2000008f) {
    if (!isnan(x[51]) && x[51] < 33.5f) {
      if (isnan(x[49]) || x[49] < 3.0f) {
        return -0.0975330397f;
      } else {
        return -0.0566579513f;
      }
    } else {
      if (!isnan(x[5]) && x[5] < 25.0666676f) {
        return -0.00712939352f;
      } else {
        return -0.0825924203f;
      }
    }
  } else {
    if (!isnan(x[0]) && x[0] < 23.5f) {
      if (isnan(x[7]) || x[7] < 24.0499992f) {
        return -0.0917971954f;
      } else {
        return -0.0426698625f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0683757737f;
      } else {
        return 0.0199139025f;
      }
    }
  }
}
static inline float indra_tree_1_33(const float *x) {
  if (!isnan(x[0]) && x[0] < 31.5f) {
    if (!isnan(x[65]) && x[65] < 0.258819044f) {
      if (isnan(x[8]) || x[8] < 31.0f) {
        return -0.101230733f;
      } else {
        return -0.0820161328f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0949803591f;
      } else {
        return 0.00866089389f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < -0.5f) {
      if (!isnan(x[0]) && x[0] < 39.0f) {
        return -0.0915421769f;
      } else {
        return 0.0295230001f;
      }
    } else {
      if (!isnan(x[71]) && x[71] < 44.0f) {
        return -0.0147201214f;
      } else {
        return 0.0788757578f;
      }
    }
  }
}
static inline float indra_tree_1_34(const float *x) {
  if (!isnan(x[61]) && x[61] < 1.45595169f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[65]) && x[65] < 0.258819044f) {
        return -0.0983732864f;
      } else {
        return -0.0662139952f;
      }
    } else {
      if (!isnan(x[0]) && x[0] < 22.6000004f) {
        return -0.0705578476f;
      } else {
        return 0.00314134918f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.258819044f) {
      if (!isnan(x[0]) && x[0] < 33.0f) {
        return -0.0713826045f;
      } else {
        return 0.0236384179f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.5f) {
        return -0.0899196267f;
      } else {
        return 0.0798718259f;
      }
    }
  }
}
static inline float indra_tree_1_35(const float *x) {
  if (!isnan(x[51]) && x[51] < 34.5999985f) {
    if (!isnan(x[51]) && x[51] < 33.5f) {
      if (isnan(x[49]) || x[49] < 3.0f) {
        return -0.0959195122f;
      } else {
        return -0.0502687357f;
      }
    } else {
      if (!isnan(x[5]) && x[5] < 25.6000004f) {
        return 0.000220741887f;
      } else {
        return -0.0761725903f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.5f) {
      if (!isnan(x[7]) && x[7] < 32.0f) {
        return -0.0780082569f;
      } else {
        return -0.00682728318f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 75.0f) {
        return 0.0520579331f;
      } else {
        return -0.00285069156f;
      }
    }
  }
}
static inline float indra_tree_1_36(const float *x) {
  if (!isnan(x[66]) && x[66] < 0.5f) {
    if (isnan(x[71]) || x[71] < 510.0f) {
      if (!isnan(x[67]) && x[67] < 6.12323426e-17f) {
        return -0.0171060916f;
      } else {
        return -0.0863537863f;
      }
    } else {
      if (!isnan(x[62]) && x[62] < 37.3675575f) {
        return -0.101229265f;
      } else {
        return -0.0557239167f;
      }
    }
  } else {
    if (!isnan(x[69]) && x[69] < 10.1520004f) {
      if (!isnan(x[7]) && x[7] < 32.5999985f) {
        return -0.113061331f;
      } else {
        return -0.0367749259f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return -0.0331360586f;
      } else {
        return 0.0237454381f;
      }
    }
  }
}
static inline float indra_tree_1_37(const float *x) {
  if (!isnan(x[7]) && x[7] < 25.0666676f) {
    if (!isnan(x[7]) && x[7] < 23.0499992f) {
      if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
        return -0.068143405f;
      } else {
        return -0.0977184996f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.866025388f) {
        return -0.0906795561f;
      } else {
        return -0.037996117f;
      }
    }
  } else {
    if (!isnan(x[60]) && x[60] < 10.1673746f) {
      if (!isnan(x[65]) && x[65] < 0.258819044f) {
        return -0.0746046826f;
      } else {
        return 0.00172458496f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.866025388f) {
        return -0.00979847554f;
      } else {
        return 0.0590076521f;
      }
    }
  }
}
static inline float indra_tree_1_38(const float *x) {
  if (!isnan(x[51]) && x[51] < 34.2000008f) {
    if (!isnan(x[51]) && x[51] < 33.5f) {
      if (isnan(x[49]) || x[49] < 3.0f) {
        return -0.093909435f;
      } else {
        return -0.0447499789f;
      }
    } else {
      if (!isnan(x[70]) && x[70] < 85.5167007f) {
        return -0.0660261139f;
      } else {
        return 0.0706027076f;
      }
    }
  } else {
    if (!isnan(x[0]) && x[0] < 23.0f) {
      if (isnan(x[12]) || x[12] < 28.291666f) {
        return -0.0705122799f;
      } else {
        return 0.0787921101f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0630083308f;
      } else {
        return 0.0151644899f;
      }
    }
  }
}
static inline float indra_tree_1_39(const float *x) {
  if (!isnan(x[69]) && x[69] < 13.0712004f) {
    if (isnan(x[51]) || x[51] < 35.0f) {
      if (!isnan(x[7]) && x[7] < 33.5f) {
        return -0.0828862414f;
      } else {
        return -0.0129509671f;
      }
    } else {
      if (!isnan(x[15]) && x[15] < 89.0f) {
        return -0.0373998061f;
      } else {
        return 0.125827447f;
      }
    }
  } else {
    if (!isnan(x[0]) && x[0] < 27.5f) {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return -0.0974245295f;
      } else {
        return -0.0165521186f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.5f) {
        return -0.0362114161f;
      } else {
        return 0.0317116641f;
      }
    }
  }
}
static inline float indra_raw_1(const float *x) {
  float margin=-2.35359294f;
  margin+=indra_tree_1_0(x);
  margin+=indra_tree_1_1(x);
  margin+=indra_tree_1_2(x);
  margin+=indra_tree_1_3(x);
  margin+=indra_tree_1_4(x);
  margin+=indra_tree_1_5(x);
  margin+=indra_tree_1_6(x);
  margin+=indra_tree_1_7(x);
  margin+=indra_tree_1_8(x);
  margin+=indra_tree_1_9(x);
  margin+=indra_tree_1_10(x);
  margin+=indra_tree_1_11(x);
  margin+=indra_tree_1_12(x);
  margin+=indra_tree_1_13(x);
  margin+=indra_tree_1_14(x);
  margin+=indra_tree_1_15(x);
  margin+=indra_tree_1_16(x);
  margin+=indra_tree_1_17(x);
  margin+=indra_tree_1_18(x);
  margin+=indra_tree_1_19(x);
  margin+=indra_tree_1_20(x);
  margin+=indra_tree_1_21(x);
  margin+=indra_tree_1_22(x);
  margin+=indra_tree_1_23(x);
  margin+=indra_tree_1_24(x);
  margin+=indra_tree_1_25(x);
  margin+=indra_tree_1_26(x);
  margin+=indra_tree_1_27(x);
  margin+=indra_tree_1_28(x);
  margin+=indra_tree_1_29(x);
  margin+=indra_tree_1_30(x);
  margin+=indra_tree_1_31(x);
  margin+=indra_tree_1_32(x);
  margin+=indra_tree_1_33(x);
  margin+=indra_tree_1_34(x);
  margin+=indra_tree_1_35(x);
  margin+=indra_tree_1_36(x);
  margin+=indra_tree_1_37(x);
  margin+=indra_tree_1_38(x);
  margin+=indra_tree_1_39(x);
  return 1.0f/(1.0f+expf(-margin));
}
static inline float indra_tree_2_0(const float *x) {
  if (!isnan(x[1]) && x[1] < 90.0f) {
    if (isnan(x[17]) || x[17] < 94.5f) {
      if (!isnan(x[60]) && x[60] < 3.41285896f) {
        return -0.0382189192f;
      } else {
        return -0.108101301f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 79.5f) {
        return 0.0784811452f;
      } else {
        return 0.223350689f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[1]) && x[1] < 94.25f) {
        return 0.270974785f;
      } else {
        return 0.402557224f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return 0.216222957f;
      } else {
        return 0.00252949586f;
      }
    }
  }
}
static inline float indra_tree_2_1(const float *x) {
  if (!isnan(x[1]) && x[1] < 89.3333359f) {
    if (isnan(x[17]) || x[17] < 94.5f) {
      if (!isnan(x[1]) && x[1] < 79.5f) {
        return -0.105769716f;
      } else {
        return -0.0406967476f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return 0.145115867f;
      } else {
        return -0.016740365f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return 0.270673215f;
      } else {
        return 0.152196392f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 95.0f) {
        return -0.0168050248f;
      } else {
        return 0.173407301f;
      }
    }
  }
}
static inline float indra_tree_2_2(const float *x) {
  if (!isnan(x[60]) && x[60] < 1.92599022f) {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[54]) && x[54] < 97.5f) {
        return 0.0538858436f;
      } else {
        return 0.214213952f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 90.0f) {
        return -0.063609682f;
      } else {
        return 0.12006738f;
      }
    }
  } else {
    if (isnan(x[17]) || x[17] < 92.0f) {
      if (!isnan(x[1]) && x[1] < 79.5f) {
        return -0.104923107f;
      } else {
        return -0.0473848209f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 96.0f) {
        return 0.000483516662f;
      } else {
        return 0.115077235f;
      }
    }
  }
}
static inline float indra_tree_2_3(const float *x) {
  if (!isnan(x[60]) && x[60] < 1.75034428f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[1]) && x[1] < 95.0f) {
        return 0.144539207f;
      } else {
        return 0.215863094f;
      }
    } else {
      if (!isnan(x[60]) && x[60] < 0.865236759f) {
        return 0.127325743f;
      } else {
        return -0.0164664518f;
      }
    }
  } else {
    if (isnan(x[17]) || x[17] < 90.0f) {
      if (!isnan(x[60]) && x[60] < 2.93583918f) {
        return -0.027502317f;
      } else {
        return -0.0988560468f;
      }
    } else {
      if (!isnan(x[60]) && x[60] < 4.49048471f) {
        return 0.0867228508f;
      } else {
        return -0.024980966f;
      }
    }
  }
}
static inline float indra_tree_2_4(const float *x) {
  if (!isnan(x[60]) && x[60] < 2.43747139f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[54]) && x[54] < 97.5f) {
        return 0.049767103f;
      } else {
        return 0.157766968f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 95.0f) {
        return -0.0399096943f;
      } else {
        return 0.107099116f;
      }
    }
  } else {
    if (isnan(x[17]) || x[17] < 92.0f) {
      if (!isnan(x[1]) && x[1] < 72.0f) {
        return -0.103798948f;
      } else {
        return -0.066441454f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 96.0f) {
        return -0.0163996946f;
      } else {
        return 0.0783342049f;
      }
    }
  }
}
static inline float indra_tree_2_5(const float *x) {
  if (!isnan(x[60]) && x[60] < 2.43747139f) {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[61]) && x[61] < 0.190066665f) {
        return 0.165485963f;
      } else {
        return 0.0697963461f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 89.3333359f) {
        return -0.0733518824f;
      } else {
        return 0.0654998943f;
      }
    }
  } else {
    if (isnan(x[17]) || x[17] < 90.0f) {
      if (!isnan(x[1]) && x[1] < 77.0f) {
        return -0.0991916955f;
      } else {
        return -0.0586706474f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 96.0f) {
        return -0.0210979562f;
      } else {
        return 0.068152748f;
      }
    }
  }
}
static inline float indra_tree_2_6(const float *x) {
  if (!isnan(x[1]) && x[1] < 84.5f) {
    if (isnan(x[17]) || x[17] < 92.0f) {
      if (!isnan(x[1]) && x[1] < 67.0f) {
        return -0.101313449f;
      } else {
        return -0.0673525184f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 98.0f) {
        return -0.0100854505f;
      } else {
        return 0.0848677829f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[54]) && x[54] < 94.6666641f) {
        return 0.00251251063f;
      } else {
        return 0.121487811f;
      }
    } else {
      if (!isnan(x[60]) && x[60] < 1.0032227f) {
        return 0.074333474f;
      } else {
        return -0.0506059602f;
      }
    }
  }
}
static inline float indra_tree_2_7(const float *x) {
  if (!isnan(x[1]) && x[1] < 92.0f) {
    if (isnan(x[17]) || x[17] < 89.3333359f) {
      if (!isnan(x[1]) && x[1] < 79.5f) {
        return -0.0911040604f;
      } else {
        return -0.0309790131f;
      }
    } else {
      if (!isnan(x[60]) && x[60] < 4.95237589f) {
        return 0.0558442175f;
      } else {
        return -0.0264037549f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[54]) && x[54] < 97.5f) {
        return 0.0337834656f;
      } else {
        return 0.134978056f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 85.0f) {
        return -0.0672374815f;
      } else {
        return 0.0653810948f;
      }
    }
  }
}
static inline float indra_tree_2_8(const float *x) {
  if (!isnan(x[1]) && x[1] < 84.5f) {
    if (isnan(x[17]) || x[17] < 90.0f) {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.0877396241f;
      } else {
        return -0.0239331275f;
      }
    } else {
      if (isnan(x[54]) || x[54] < 100.0f) {
        return -0.0197950844f;
      } else {
        return 0.0721670538f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[1]) && x[1] < 94.25f) {
        return 0.0733370185f;
      } else {
        return 0.133740395f;
      }
    } else {
      if (!isnan(x[61]) && x[61] < 0.109097198f) {
        return 0.0723174438f;
      } else {
        return -0.0404799245f;
      }
    }
  }
}
static inline float indra_tree_2_9(const float *x) {
  if (!isnan(x[61]) && x[61] < 0.288591057f) {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[54]) && x[54] < 95.5f) {
        return -0.00156743755f;
      } else {
        return 0.111848786f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 85.0f) {
        return -0.0794617608f;
      } else {
        return 0.0403571241f;
      }
    }
  } else {
    if (isnan(x[17]) || x[17] < 89.3333359f) {
      if (!isnan(x[1]) && x[1] < 77.0f) {
        return -0.0888079628f;
      } else {
        return -0.0353614651f;
      }
    } else {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.00551932864f;
      } else {
        return 0.0772282854f;
      }
    }
  }
}
static inline float indra_tree_2_10(const float *x) {
  if (!isnan(x[1]) && x[1] < 84.5f) {
    if (isnan(x[17]) || x[17] < 90.0f) {
      if (!isnan(x[1]) && x[1] < 67.0f) {
        return -0.0932081789f;
      } else {
        return -0.0551518314f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 96.0f) {
        return -0.0248104315f;
      } else {
        return 0.0450763144f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[18]) && x[18] < 90.0f) {
        return 0.0509809814f;
      } else {
        return 0.104794614f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 92.0f) {
        return -0.0671371222f;
      } else {
        return 0.0316544846f;
      }
    }
  }
}
static inline float indra_tree_2_11(const float *x) {
  if (!isnan(x[60]) && x[60] < 2.93583918f) {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[61]) && x[61] < 0.168566257f) {
        return 0.10941346f;
      } else {
        return 0.0399496071f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -1.83697015e-16f) {
        return 0.0709259957f;
      } else {
        return -0.0432948433f;
      }
    }
  } else {
    if (!isnan(x[17]) && x[17] < 84.5f) {
      if (isnan(x[54]) || x[54] < 94.5f) {
        return -0.0897380486f;
      } else {
        return 0.076165773f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return 0.00104094448f;
      } else {
        return -0.0723020509f;
      }
    }
  }
}
static inline float indra_tree_2_12(const float *x) {
  if (!isnan(x[60]) && x[60] < 3.41285896f) {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[54]) && x[54] < 97.5f) {
        return -0.00173057651f;
      } else {
        return 0.0754506215f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 92.0f) {
        return -0.069700934f;
      } else {
        return 0.0269103553f;
      }
    }
  } else {
    if (!isnan(x[17]) && x[17] < 86.0f) {
      if (isnan(x[54]) || x[54] < 94.5f) {
        return -0.0903826952f;
      } else {
        return 0.071435526f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return -0.00524332607f;
      } else {
        return -0.0740292445f;
      }
    }
  }
}
static inline float indra_tree_2_13(const float *x) {
  if (!isnan(x[1]) && x[1] < 79.5f) {
    if (!isnan(x[70]) && x[70] < 85.8178024f) {
      if (!isnan(x[1]) && x[1] < 64.0f) {
        return -0.091671668f;
      } else {
        return -0.0481853224f;
      }
    } else {
      if (!isnan(x[9]) && x[9] < 0.233333334f) {
        return 0.159794256f;
      } else {
        return -0.0398064964f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[18]) && x[18] < 90.0f) {
        return 0.0332440808f;
      } else {
        return 0.0842542574f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 92.0f) {
        return -0.0681616738f;
      } else {
        return 0.0240232591f;
      }
    }
  }
}
static inline float indra_tree_2_14(const float *x) {
  if (!isnan(x[1]) && x[1] < 77.0f) {
    if (isnan(x[54]) || x[54] < 100.0f) {
      if (!isnan(x[17]) && x[17] < 86.0f) {
        return -0.0912116393f;
      } else {
        return -0.0465364568f;
      }
    } else {
      if (!isnan(x[70]) && x[70] < 85.5167007f) {
        return -0.0165813025f;
      } else {
        return 0.151527151f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.5f) {
      if (!isnan(x[54]) && x[54] < 94.5f) {
        return -0.0321619213f;
      } else {
        return 0.0580919981f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 94.25f) {
        return -0.0479099676f;
      } else {
        return 0.0461847559f;
      }
    }
  }
}
static inline float indra_tree_2_15(const float *x) {
  if (!isnan(x[61]) && x[61] < 0.261345178f) {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (!isnan(x[45]) && x[45] < 97.0f) {
        return 0.0382985808f;
      } else {
        return 0.09316957f;
      }
    } else {
      if (isnan(x[17]) || x[17] < 94.5f) {
        return -0.0253704768f;
      } else {
        return 0.0925053582f;
      }
    }
  } else {
    if (!isnan(x[1]) && x[1] < 67.0f) {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.0847260058f;
      } else {
        return -0.00125256658f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return 0.014474513f;
      } else {
        return -0.0733639598f;
      }
    }
  }
}
static inline float indra_tree_2_16(const float *x) {
  if (!isnan(x[1]) && x[1] < 77.0f) {
    if (!isnan(x[17]) && x[17] < 86.0f) {
      if (isnan(x[54]) || x[54] < 98.0f) {
        return -0.0878293142f;
      } else {
        return 0.152270094f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.5f) {
        return -0.00203291257f;
      } else {
        return -0.0659672916f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[61]) && x[61] < 0.168566257f) {
        return 0.0854936615f;
      } else {
        return 0.0191964395f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -1.83697015e-16f) {
        return 0.0488233306f;
      } else {
        return -0.0473573841f;
      }
    }
  }
}
static inline float indra_tree_2_17(const float *x) {
  if (!isnan(x[61]) && x[61] < 0.230726302f) {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (isnan(x[4]) || x[4] < 14.0f) {
        return 0.0901486576f;
      } else {
        return 0.041918233f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 84.0f) {
        return -0.0715121552f;
      } else {
        return 0.0324049555f;
      }
    }
  } else {
    if (!isnan(x[70]) && x[70] < 85.8178024f) {
      if (!isnan(x[1]) && x[1] < 64.0f) {
        return -0.0838674456f;
      } else {
        return -0.0265280735f;
      }
    } else {
      if (!isnan(x[40]) && x[40] < 8.19999981f) {
        return 0.105624259f;
      } else {
        return -0.0132558374f;
      }
    }
  }
}
static inline float indra_tree_2_18(const float *x) {
  if (!isnan(x[18]) && x[18] < 90.0f) {
    if (!isnan(x[1]) && x[1] < 64.0f) {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.0827608556f;
      } else {
        return -0.00441973051f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -1.83697015e-16f) {
        return 0.0218866691f;
      } else {
        return -0.0475676805f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (isnan(x[18]) || x[18] < 95.0f) {
        return 0.0477045439f;
      } else {
        return 0.0956814811f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 92.0f) {
        return -0.0527685396f;
      } else {
        return 0.0400881022f;
      }
    }
  }
}
static inline float indra_tree_2_19(const float *x) {
  if (!isnan(x[1]) && x[1] < 75.0f) {
    if (!isnan(x[17]) && x[17] < 86.0f) {
      if (isnan(x[54]) || x[54] < 98.0f) {
        return -0.0847605988f;
      } else {
        return 0.122921944f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.5f) {
        return 0.000363689353f;
      } else {
        return -0.0615327917f;
      }
    }
  } else {
    if (isnan(x[17]) || x[17] < 94.5f) {
      if (!isnan(x[64]) && x[64] < -0.5f) {
        return 0.0355255231f;
      } else {
        return -0.0219376124f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return 0.0844131634f;
      } else {
        return 0.0250657536f;
      }
    }
  }
}
static inline float indra_tree_2_20(const float *x) {
  if (!isnan(x[1]) && x[1] < 94.25f) {
    if (isnan(x[54]) || x[54] < 97.5f) {
      if (!isnan(x[1]) && x[1] < 64.0f) {
        return -0.0731297582f;
      } else {
        return -0.0160378125f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.866025388f) {
        return 0.0654870793f;
      } else {
        return -0.0477552228f;
      }
    }
  } else {
    if (isnan(x[15]) || x[15] < 95.0f) {
      if (!isnan(x[65]) && x[65] < 0.707106769f) {
        return 0.0601437464f;
      } else {
        return -0.00987310056f;
      }
    } else {
      if (!isnan(x[22]) && x[22] < 94.4375f) {
        return 0.0314453468f;
      } else {
        return 0.0853463039f;
      }
    }
  }
}
static inline float indra_tree_2_21(const float *x) {
  if (isnan(x[18]) || x[18] < 94.25f) {
    if (!isnan(x[54]) && x[54] < 94.5f) {
      if (!isnan(x[64]) && x[64] < -0.5f) {
        return -0.0349993855f;
      } else {
        return -0.0866925865f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.258819044f) {
        return 0.0174148045f;
      } else {
        return -0.0305432025f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.258819044f) {
      if (isnan(x[7]) || x[7] < 21.3500004f) {
        return 0.111156344f;
      } else {
        return 0.0708768964f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
        return 0.0725617632f;
      } else {
        return -0.0247006025f;
      }
    }
  }
}
static inline float indra_tree_2_22(const float *x) {
  if (isnan(x[16]) || x[16] < 94.3333359f) {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[61]) && x[61] < 0.507265985f) {
        return 0.0301383268f;
      } else {
        return -0.0333451703f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 81.0f) {
        return -0.0868187845f;
      } else {
        return -0.0187001079f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (!isnan(x[33]) && x[33] < 76.2000122f) {
        return 0.0833657086f;
      } else {
        return 0.216495425f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 23.0f) {
        return -0.0777091831f;
      } else {
        return 0.0378715843f;
      }
    }
  }
}
static inline float indra_tree_2_23(const float *x) {
  if (!isnan(x[1]) && x[1] < 95.0f) {
    if (!isnan(x[1]) && x[1] < 55.0f) {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.0832593888f;
      } else {
        return -0.00230210414f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return 0.0122466935f;
      } else {
        return -0.0445361026f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < -0.5f) {
      if (!isnan(x[20]) && x[20] < 95.3333359f) {
        return 0.0550559424f;
      } else {
        return 0.0912650898f;
      }
    } else {
      if (!isnan(x[22]) && x[22] < 87.9166641f) {
        return -0.0886532292f;
      } else {
        return 0.0418519042f;
      }
    }
  }
}
static inline float indra_tree_2_24(const float *x) {
  if (!isnan(x[54]) && x[54] < 94.5f) {
    if (!isnan(x[64]) && x[64] < -0.5f) {
      if (!isnan(x[61]) && x[61] < 0.656461835f) {
        return -0.00971993059f;
      } else {
        return -0.0753508136f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 79.3333359f) {
        return -0.0960789695f;
      } else {
        return -0.0635626316f;
      }
    }
  } else {
    if (!isnan(x[1]) && x[1] < 63.0f) {
      if (isnan(x[19]) || x[19] < 2.0f) {
        return -0.0657247528f;
      } else {
        return 0.0599492379f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 19.9666996f) {
        return -0.0151936514f;
      } else {
        return 0.0320392214f;
      }
    }
  }
}
static inline float indra_tree_2_25(const float *x) {
  if (isnan(x[17]) || x[17] < 94.5f) {
    if (!isnan(x[1]) && x[1] < 69.5f) {
      if (!isnan(x[70]) && x[70] < 94.0976028f) {
        return -0.060698159f;
      } else {
        return 0.0937847421f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return 0.01665272f;
      } else {
        return -0.0249659773f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (!isnan(x[61]) && x[61] < 0.288591057f) {
        return 0.0788047463f;
      } else {
        return 0.0388559252f;
      }
    } else {
      if (!isnan(x[1]) && x[1] < 97.0f) {
        return -0.0275088642f;
      } else {
        return 0.0674124733f;
      }
    }
  }
}
static inline float indra_tree_2_26(const float *x) {
  if (isnan(x[16]) || x[16] < 94.3333359f) {
    if (!isnan(x[64]) && x[64] < 0.0f) {
      if (!isnan(x[61]) && x[61] < 0.440624535f) {
        return 0.0274970084f;
      } else {
        return -0.0246005449f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 80.0f) {
        return -0.0827571228f;
      } else {
        return -0.0156640876f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (!isnan(x[17]) && x[17] < 200.0f) {
        return 0.0710086152f;
      } else {
        return 0.192942083f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 21.3500004f) {
        return -0.0835955739f;
      } else {
        return 0.0296917893f;
      }
    }
  }
}
static inline float indra_tree_2_27(const float *x) {
  if (!isnan(x[54]) && x[54] < 94.5f) {
    if (!isnan(x[64]) && x[64] < -0.5f) {
      if (!isnan(x[71]) && x[71] < 12.0f) {
        return 0.0532218814f;
      } else {
        return -0.0392374694f;
      }
    } else {
      if (!isnan(x[22]) && x[22] < 77.4375f) {
        return -0.0905887559f;
      } else {
        return -0.0548578985f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (!isnan(x[17]) && x[17] < 79.3333359f) {
        return -0.0127622085f;
      } else {
        return 0.0389342867f;
      }
    } else {
      if (!isnan(x[63]) && x[63] < 20.4608898f) {
        return -0.0590439998f;
      } else {
        return 0.0115356641f;
      }
    }
  }
}
static inline float indra_tree_2_28(const float *x) {
  if (isnan(x[18]) || x[18] < 95.0f) {
    if (!isnan(x[1]) && x[1] < 49.5f) {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.083784692f;
      } else {
        return 1.65478759e-05f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 0.5f) {
        return 0.00999346934f;
      } else {
        return -0.0362489186f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.258819044f) {
      if (!isnan(x[63]) && x[63] < 10.616951f) {
        return 0.100562118f;
      } else {
        return 0.0562738962f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
        return 0.0589773953f;
      } else {
        return -0.0214556679f;
      }
    }
  }
}
static inline float indra_tree_2_29(const float *x) {
  if (!isnan(x[54]) && x[54] < 94.5f) {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (!isnan(x[51]) && x[51] < 23.0f) {
        return 0.0671775565f;
      } else {
        return -0.0381389f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 81.0f) {
        return -0.0950580388f;
      } else {
        return -0.0589760952f;
      }
    }
  } else {
    if (!isnan(x[69]) && x[69] < 28.0f) {
      if (!isnan(x[63]) && x[63] < 19.7605934f) {
        return -0.0318642035f;
      } else {
        return 0.0136092901f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.866025388f) {
        return 0.0627994165f;
      } else {
        return -0.0106249303f;
      }
    }
  }
}
static inline float indra_tree_2_30(const float *x) {
  if (!isnan(x[18]) && x[18] < 90.0f) {
    if (!isnan(x[65]) && x[65] < -1.83697015e-16f) {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.0124183688f;
      } else {
        return 0.0660918429f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return -0.0130089065f;
      } else {
        return -0.0694699958f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < -0.5f) {
      if (!isnan(x[15]) && x[15] < 95.0f) {
        return 0.0419922844f;
      } else {
        return 0.0840855762f;
      }
    } else {
      if (!isnan(x[22]) && x[22] < 85.375f) {
        return -0.0859647244f;
      } else {
        return 0.0120695112f;
      }
    }
  }
}
static inline float indra_tree_2_31(const float *x) {
  if (!isnan(x[61]) && x[61] < 0.140296876f) {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (isnan(x[4]) || x[4] < 14.0f) {
        return 0.0745937973f;
      } else {
        return 0.0305469688f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
        return 0.0491463728f;
      } else {
        return -0.0182456635f;
      }
    }
  } else {
    if (!isnan(x[17]) && x[17] < 69.0f) {
      if (!isnan(x[64]) && x[64] < -0.5f) {
        return -0.00954830833f;
      } else {
        return -0.0769560859f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.707106769f) {
        return 0.0122302482f;
      } else {
        return -0.0316754393f;
      }
    }
  }
}
static inline float indra_tree_2_32(const float *x) {
  if (isnan(x[16]) || x[16] < 95.0f) {
    if (!isnan(x[1]) && x[1] < 49.5f) {
      if (!isnan(x[70]) && x[70] < 85.8178024f) {
        return -0.083003588f;
      } else {
        return -0.00372592034f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 19.9666996f) {
        return -0.0273511168f;
      } else {
        return 0.0123688448f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.866025388f) {
      if (!isnan(x[69]) && x[69] < 27.2954998f) {
        return 0.048804231f;
      } else {
        return 0.111503601f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 21.3500004f) {
        return -0.0671448186f;
      } else {
        return 0.0273095816f;
      }
    }
  }
}
static inline float indra_tree_2_33(const float *x) {
  if (!isnan(x[54]) && x[54] < 94.5f) {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (!isnan(x[67]) && x[67] < 1.0f) {
        return -0.0371774696f;
      } else {
        return 0.0387266353f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 81.0f) {
        return -0.0916943774f;
      } else {
        return -0.0533580072f;
      }
    }
  } else {
    if (!isnan(x[69]) && x[69] < 28.0f) {
      if (!isnan(x[63]) && x[63] < 19.7605934f) {
        return -0.02749517f;
      } else {
        return 0.0116809634f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 30.3999996f) {
        return 0.0627905354f;
      } else {
        return -0.00263628527f;
      }
    }
  }
}
static inline float indra_tree_2_34(const float *x) {
  if (isnan(x[15]) || x[15] < 95.0f) {
    if (!isnan(x[65]) && x[65] < 0.707106769f) {
      if (!isnan(x[64]) && x[64] < 0.866025388f) {
        return 0.01307928f;
      } else {
        return -0.0362355895f;
      }
    } else {
      if (!isnan(x[69]) && x[69] < 28.0f) {
        return -0.0515687428f;
      } else {
        return 0.0274141617f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (!isnan(x[5]) && x[5] < 12.0f) {
        return 0.107219391f;
      } else {
        return 0.0460590236f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 22.3999996f) {
        return -0.0574520789f;
      } else {
        return 0.0299808811f;
      }
    }
  }
}
static inline float indra_tree_2_35(const float *x) {
  if (!isnan(x[54]) && x[54] < 92.5f) {
    if (!isnan(x[70]) && x[70] < 77.6500015f) {
      if (!isnan(x[71]) && x[71] < 12.0f) {
        return 0.00707757799f;
      } else {
        return -0.0849405751f;
      }
    } else {
      if (!isnan(x[22]) && x[22] < 77.4375f) {
        return -0.051917661f;
      } else {
        return 0.0521986969f;
      }
    }
  } else {
    if (!isnan(x[69]) && x[69] < 19.9666996f) {
      if (!isnan(x[71]) && x[71] < 47.0f) {
        return -0.00128884823f;
      } else {
        return -0.0499187857f;
      }
    } else {
      if (!isnan(x[60]) && x[60] < 11.5169735f) {
        return 0.0194756892f;
      } else {
        return -0.054687541f;
      }
    }
  }
}
static inline float indra_tree_2_36(const float *x) {
  if (!isnan(x[17]) && x[17] < 84.5f) {
    if (!isnan(x[64]) && x[64] < -0.258819044f) {
      if (!isnan(x[61]) && x[61] < 0.475166649f) {
        return 0.0208492465f;
      } else {
        return -0.0373963229f;
      }
    } else {
      if (!isnan(x[17]) && x[17] < 76.0f) {
        return -0.075933069f;
      } else {
        return -0.0334954001f;
      }
    }
  } else {
    if (!isnan(x[64]) && x[64] < 0.707106769f) {
      if (!isnan(x[54]) && x[54] < 97.5f) {
        return -0.0252521522f;
      } else {
        return 0.033524055f;
      }
    } else {
      if (!isnan(x[63]) && x[63] < 19.3462467f) {
        return -0.0431531742f;
      } else {
        return 0.0105045978f;
      }
    }
  }
}
static inline float indra_tree_2_37(const float *x) {
  if (!isnan(x[1]) && x[1] < 43.0f) {
    if (isnan(x[54]) || x[54] < 100.0f) {
      if (!isnan(x[4]) && x[4] < 19.1000004f) {
        return 0.0618652105f;
      } else {
        return -0.0888691619f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.5f) {
        return 0.101350211f;
      } else {
        return -0.0536260493f;
      }
    }
  } else {
    if (!isnan(x[69]) && x[69] < 19.9666996f) {
      if (!isnan(x[71]) && x[71] < 47.0f) {
        return -0.00455889665f;
      } else {
        return -0.0445695631f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < -0.258819044f) {
        return 0.0374617465f;
      } else {
        return 0.00257834769f;
      }
    }
  }
}
static inline float indra_tree_2_38(const float *x) {
  if (!isnan(x[61]) && x[61] < 0.0736777559f) {
    if (!isnan(x[4]) && x[4] < 28.5f) {
      if (!isnan(x[64]) && x[64] < 0.258819044f) {
        return 0.0365565605f;
      } else {
        return -0.0155419977f;
      }
    } else {
      if (!isnan(x[67]) && x[67] < -1.83697015e-16f) {
        return 0.0869229212f;
      } else {
        return 0.0357404537f;
      }
    }
  } else {
    if (!isnan(x[65]) && x[65] < 0.707106769f) {
      if (!isnan(x[70]) && x[70] < 76.4019012f) {
        return -0.0319863521f;
      } else {
        return 0.0135902753f;
      }
    } else {
      if (!isnan(x[7]) && x[7] < 30.5f) {
        return -0.0142280404f;
      } else {
        return -0.0631041825f;
      }
    }
  }
}
static inline float indra_tree_2_39(const float *x) {
  if (!isnan(x[1]) && x[1] < 43.0f) {
    if (isnan(x[54]) || x[54] < 94.0f) {
      if (!isnan(x[4]) && x[4] < 19.1000004f) {
        return 0.0564007834f;
      } else {
        return -0.089038305f;
      }
    } else {
      if (!isnan(x[64]) && x[64] < 0.5f) {
        return 0.0798228905f;
      } else {
        return -0.0624767542f;
      }
    }
  } else {
    if (!isnan(x[17]) && x[17] < 94.5f) {
      if (!isnan(x[64]) && x[64] < -0.258819044f) {
        return 0.00810673274f;
      } else {
        return -0.0290948655f;
      }
    } else {
      if (!isnan(x[65]) && x[65] < 6.12323426e-17f) {
        return 0.0435137115f;
      } else {
        return -0.00750052044f;
      }
    }
  }
}
static inline float indra_raw_2(const float *x) {
  float margin=-1.30659477f;
  margin+=indra_tree_2_0(x);
  margin+=indra_tree_2_1(x);
  margin+=indra_tree_2_2(x);
  margin+=indra_tree_2_3(x);
  margin+=indra_tree_2_4(x);
  margin+=indra_tree_2_5(x);
  margin+=indra_tree_2_6(x);
  margin+=indra_tree_2_7(x);
  margin+=indra_tree_2_8(x);
  margin+=indra_tree_2_9(x);
  margin+=indra_tree_2_10(x);
  margin+=indra_tree_2_11(x);
  margin+=indra_tree_2_12(x);
  margin+=indra_tree_2_13(x);
  margin+=indra_tree_2_14(x);
  margin+=indra_tree_2_15(x);
  margin+=indra_tree_2_16(x);
  margin+=indra_tree_2_17(x);
  margin+=indra_tree_2_18(x);
  margin+=indra_tree_2_19(x);
  margin+=indra_tree_2_20(x);
  margin+=indra_tree_2_21(x);
  margin+=indra_tree_2_22(x);
  margin+=indra_tree_2_23(x);
  margin+=indra_tree_2_24(x);
  margin+=indra_tree_2_25(x);
  margin+=indra_tree_2_26(x);
  margin+=indra_tree_2_27(x);
  margin+=indra_tree_2_28(x);
  margin+=indra_tree_2_29(x);
  margin+=indra_tree_2_30(x);
  margin+=indra_tree_2_31(x);
  margin+=indra_tree_2_32(x);
  margin+=indra_tree_2_33(x);
  margin+=indra_tree_2_34(x);
  margin+=indra_tree_2_35(x);
  margin+=indra_tree_2_36(x);
  margin+=indra_tree_2_37(x);
  margin+=indra_tree_2_38(x);
  margin+=indra_tree_2_39(x);
  return 1.0f/(1.0f+expf(-margin));
}
/* Caller supplies exact ordered float32 features. Missing optional features use NAN; infinities refuse. */
static inline int indra_india_predict(const float *x, float *raw, float *prob, int *flags, uint8_t *status) {
  if (!x || !raw || !prob || !flags || !status) return 0;
  for (int h=0;h<INDRA_INDIA_HEADS;++h) { raw[h]=prob[h]=NAN; flags[h]=-1; status[h]=INDRA_UNTRAINED; }
  for (int i=0;i<INDRA_INDIA_FEATURES;++i) if (isinf(x[i])) return 0;
  if (!isfinite(x[0])) { for (int h=0;h<INDRA_INDIA_HEADS;++h) status[h]=INDRA_INVALID_CORE; return 0; }
  if (!isfinite(x[1])) { for (int h=0;h<INDRA_INDIA_HEADS;++h) status[h]=INDRA_INVALID_CORE; return 0; }
  if (!isfinite(x[3])) { for (int h=0;h<INDRA_INDIA_HEADS;++h) status[h]=INDRA_INVALID_CORE; return 0; }
  if ((!isnan(x[0]) && (x[0] < -16.0f || x[0] > 48.5f)) || (!isnan(x[1]) && (x[1] < 3.0f || x[1] > 100.0f)) || (!isnan(x[2]) && (x[2] < 499.700012f || x[2] > 1090.19995f)) || (!isnan(x[3]) && (x[3] < 0.0f || x[3] > 32.4000015f)) || (!isnan(x[4]) && (x[4] < -20.0f || x[4] > 46.5999985f)) || (!isnan(x[5]) && (x[5] < -16.0f || x[5] > 48.4000015f)) || (!isnan(x[6]) && (x[6] < -16.0f || x[6] > 48.5f)) || (!isnan(x[7]) && (x[7] < -14.0f || x[7] > 48.5f)) || (!isnan(x[8]) && (x[8] < -15.6000004f || x[8] > 48.5f)) || (!isnan(x[9]) && (x[9] < -13.75f || x[9] > 15.3999996f)) || (!isnan(x[10]) && (x[10] < -12.8500004f || x[10] > 45.5583344f)) || (!isnan(x[11]) && (x[11] < 0.0f || x[11] > 8.67187309f)) || (!isnan(x[12]) && (x[12] < 6.35208321f || x[12] > 40.0708351f)) || (!isnan(x[13]) && (x[13] < 0.122474484f || x[13] > 7.16749001f)) || (!isnan(x[14]) && (x[14] < 4.0f || x[14] > 100.0f)) || (!isnan(x[15]) && (x[15] < 4.0f || x[15] > 100.0f)) || (!isnan(x[16]) && (x[16] < 3.0f || x[16] > 100.0f)) || (!isnan(x[17]) && (x[17] < 3.0f || x[17] > 100.0f)) || (!isnan(x[18]) && (x[18] < 3.0f || x[18] > 100.0f)) || (!isnan(x[19]) && (x[19] < -60.0f || x[19] > 56.5f)) || (!isnan(x[20]) && (x[20] < 6.0f || x[20] > 100.0f)) || (!isnan(x[21]) && (x[21] < 0.0f || x[21] > 31.7227573f)) || (!isnan(x[22]) && (x[22] < 14.791667f || x[22] > 100.0f)) || (!isnan(x[23]) && (x[23] < 0.0f || x[23] > 35.2908974f)) || (!isnan(x[24]) && (x[24] < 647.700012f || x[24] > 1050.19995f)) || (!isnan(x[25]) && (x[25] < 499.700012f || x[25] > 1050.19995f)) || (!isnan(x[26]) && (x[26] < 499.700012f || x[26] > 1090.19995f)) || (!isnan(x[27]) && (x[27] < 499.700012f || x[27] > 1090.19995f)) || (!isnan(x[28]) && (x[28] < 499.700012f || x[28] > 1090.19995f)) || (!isnan(x[29]) && (x[29] < -1.79999995f || x[29] > -1.5f)) || (!isnan(x[30]) && (x[30] < 0.0f || x[30] > 32.4000015f)) || (!isnan(x[31]) && (x[31] < 0.0f || x[31] > 38.0999985f)) || (!isnan(x[32]) && (x[32] < 0.0f || x[32] > 38.0999985f)) || (!isnan(x[33]) && (x[33] < 0.0f || x[33] > 38.0999985f)) || (!isnan(x[34]) && (x[34] < 0.0f || x[34] > 38.0999985f)) || (!isnan(x[35]) && (x[35] < -28.7999992f || x[35] > 12.6000004f)) || (!isnan(x[36]) && (x[36] < 0.0f || x[36] > 13.1333332f)) || (!isnan(x[37]) && (x[37] < 0.0f || x[37] > 11.3375483f)) || (!isnan(x[38]) && (x[38] < 0.0f || x[38] > 7.76041651f)) || (!isnan(x[39]) && (x[39] < 0.0f || x[39] > 3.96652436f)) || (!isnan(x[40]) && (x[40] < -17.3500004f || x[40] > 24.0f)) || (!isnan(x[41]) && (x[41] < -17.5f || x[41] > 45.0f)) || (!isnan(x[42]) && (x[42] < -7.0f || x[42] > 46.5999985f)) || (!isnan(x[43]) && (x[43] < -81.5f || x[43] > 82.5f)) || (!isnan(x[44]) && (x[44] < 4.0f || x[44] > 100.0f)) || (!isnan(x[45]) && (x[45] < 7.5f || x[45] > 100.0f)) || (!isnan(x[46]) && (x[46] < -29.7999992f || x[46] > 14.8999996f)) || (!isnan(x[47]) && (x[47] < 0.0f || x[47] > 11.8500004f)) || (!isnan(x[48]) && (x[48] < 0.0f || x[48] > 32.4000015f)) || (!isnan(x[49]) && (x[49] < -19.5f || x[49] > 13.3500004f)) || (!isnan(x[50]) && (x[50] < 1.70000005f || x[50] > 35.75f)) || (!isnan(x[51]) && (x[51] < 8.80000019f || x[51] > 46.5999985f)) || (!isnan(x[52]) && (x[52] < -64.0f || x[52] > 69.5f)) || (!isnan(x[53]) && (x[53] < 6.0f || x[53] > 100.0f)) || (!isnan(x[54]) && (x[54] < 22.5f || x[54] > 100.0f)) || (!isnan(x[55]) && (x[55] < -15.1999998f || x[55] > 13.6000004f)) || (!isnan(x[56]) && (x[56] < 0.0f || x[56] > 6.19999981f)) || (!isnan(x[57]) && (x[57] < 0.0f || x[57] > 17.5f)) || (!isnan(x[58]) && (x[58] < -0.0299999993f || x[58] > -0.0250000004f)) || (!isnan(x[59]) && (x[59] < -33.8489342f || x[59] > 33.7245483f)) || (!isnan(x[60]) && (x[60] < -7.10542736e-15f || x[60] > 53.9953384f)) || (!isnan(x[61]) && (x[61] < 0.0f || x[61] > 10.7600718f)) || (!isnan(x[62]) && (x[62] < -16.0f || x[62] > 78.936821f)) || (!isnan(x[63]) && (x[63] < 0.277918696f || x[63] > 35.6330299f)) || (!isnan(x[64]) && (x[64] < -1.0f || x[64] > 1.0f)) || (!isnan(x[65]) && (x[65] < -1.0f || x[65] > 1.0f)) || (!isnan(x[66]) && (x[66] < -1.0f || x[66] > 1.0f)) || (!isnan(x[67]) && (x[67] < -1.0f || x[67] > 1.0f)) || (!isnan(x[68]) && (x[68] < 0.0f || x[68] > 1.0f)) || (!isnan(x[69]) && (x[69] < 7.9833f || x[69] > 34.1359f)) || (!isnan(x[70]) && (x[70] < 68.85f || x[70] > 95.3833f)) || (!isnan(x[71]) && (x[71] < 0.0f || x[71] > 3258.0f))) status[0]=INDRA_OOD;
  else {
    raw[0]=indra_raw_0(x);
    status[0]=INDRA_UNCALIBRATED;
    flags[0]=(raw[0] >= 0.0217449348f);
  }
  if ((!isnan(x[0]) && (x[0] < -16.0f || x[0] > 48.5f)) || (!isnan(x[1]) && (x[1] < 3.0f || x[1] > 100.0f)) || (!isnan(x[2]) && (x[2] < 499.700012f || x[2] > 1090.19995f)) || (!isnan(x[3]) && (x[3] < 0.0f || x[3] > 32.4000015f)) || (!isnan(x[4]) && (x[4] < -20.0f || x[4] > 46.5999985f)) || (!isnan(x[5]) && (x[5] < -16.0f || x[5] > 48.4000015f)) || (!isnan(x[6]) && (x[6] < -16.0f || x[6] > 48.5f)) || (!isnan(x[7]) && (x[7] < -14.0f || x[7] > 48.5f)) || (!isnan(x[8]) && (x[8] < -15.6000004f || x[8] > 48.5f)) || (!isnan(x[9]) && (x[9] < -13.75f || x[9] > 15.3999996f)) || (!isnan(x[10]) && (x[10] < -12.8500004f || x[10] > 45.5583344f)) || (!isnan(x[11]) && (x[11] < 0.0f || x[11] > 8.67187309f)) || (!isnan(x[12]) && (x[12] < 6.35208321f || x[12] > 40.0708351f)) || (!isnan(x[13]) && (x[13] < 0.122474484f || x[13] > 7.16749001f)) || (!isnan(x[14]) && (x[14] < 4.0f || x[14] > 100.0f)) || (!isnan(x[15]) && (x[15] < 4.0f || x[15] > 100.0f)) || (!isnan(x[16]) && (x[16] < 3.0f || x[16] > 100.0f)) || (!isnan(x[17]) && (x[17] < 3.0f || x[17] > 100.0f)) || (!isnan(x[18]) && (x[18] < 3.0f || x[18] > 100.0f)) || (!isnan(x[19]) && (x[19] < -60.0f || x[19] > 56.5f)) || (!isnan(x[20]) && (x[20] < 6.0f || x[20] > 100.0f)) || (!isnan(x[21]) && (x[21] < 0.0f || x[21] > 31.7227573f)) || (!isnan(x[22]) && (x[22] < 14.791667f || x[22] > 100.0f)) || (!isnan(x[23]) && (x[23] < 0.0f || x[23] > 35.2908974f)) || (!isnan(x[24]) && (x[24] < 647.700012f || x[24] > 1050.19995f)) || (!isnan(x[25]) && (x[25] < 499.700012f || x[25] > 1050.19995f)) || (!isnan(x[26]) && (x[26] < 499.700012f || x[26] > 1090.19995f)) || (!isnan(x[27]) && (x[27] < 499.700012f || x[27] > 1090.19995f)) || (!isnan(x[28]) && (x[28] < 499.700012f || x[28] > 1090.19995f)) || (!isnan(x[29]) && (x[29] < -1.79999995f || x[29] > -1.5f)) || (!isnan(x[30]) && (x[30] < 0.0f || x[30] > 32.4000015f)) || (!isnan(x[31]) && (x[31] < 0.0f || x[31] > 38.0999985f)) || (!isnan(x[32]) && (x[32] < 0.0f || x[32] > 38.0999985f)) || (!isnan(x[33]) && (x[33] < 0.0f || x[33] > 38.0999985f)) || (!isnan(x[34]) && (x[34] < 0.0f || x[34] > 38.0999985f)) || (!isnan(x[35]) && (x[35] < -28.7999992f || x[35] > 12.6000004f)) || (!isnan(x[36]) && (x[36] < 0.0f || x[36] > 13.1333332f)) || (!isnan(x[37]) && (x[37] < 0.0f || x[37] > 11.3375483f)) || (!isnan(x[38]) && (x[38] < 0.0f || x[38] > 7.76041651f)) || (!isnan(x[39]) && (x[39] < 0.0f || x[39] > 3.96652436f)) || (!isnan(x[40]) && (x[40] < -17.3500004f || x[40] > 24.0f)) || (!isnan(x[41]) && (x[41] < -17.5f || x[41] > 45.0f)) || (!isnan(x[42]) && (x[42] < -7.0f || x[42] > 46.5999985f)) || (!isnan(x[43]) && (x[43] < -81.5f || x[43] > 82.5f)) || (!isnan(x[44]) && (x[44] < 4.0f || x[44] > 100.0f)) || (!isnan(x[45]) && (x[45] < 7.5f || x[45] > 100.0f)) || (!isnan(x[46]) && (x[46] < -29.7999992f || x[46] > 14.8999996f)) || (!isnan(x[47]) && (x[47] < 0.0f || x[47] > 11.8500004f)) || (!isnan(x[48]) && (x[48] < 0.0f || x[48] > 32.4000015f)) || (!isnan(x[49]) && (x[49] < -19.5f || x[49] > 13.3500004f)) || (!isnan(x[50]) && (x[50] < 1.70000005f || x[50] > 35.75f)) || (!isnan(x[51]) && (x[51] < 8.80000019f || x[51] > 46.5999985f)) || (!isnan(x[52]) && (x[52] < -64.0f || x[52] > 69.5f)) || (!isnan(x[53]) && (x[53] < 6.0f || x[53] > 100.0f)) || (!isnan(x[54]) && (x[54] < 22.5f || x[54] > 100.0f)) || (!isnan(x[55]) && (x[55] < -15.1999998f || x[55] > 13.6000004f)) || (!isnan(x[56]) && (x[56] < 0.0f || x[56] > 6.19999981f)) || (!isnan(x[57]) && (x[57] < 0.0f || x[57] > 17.5f)) || (!isnan(x[58]) && (x[58] < -0.0299999993f || x[58] > -0.0250000004f)) || (!isnan(x[59]) && (x[59] < -33.8489342f || x[59] > 33.7245483f)) || (!isnan(x[60]) && (x[60] < -7.10542736e-15f || x[60] > 53.9953384f)) || (!isnan(x[61]) && (x[61] < 0.0f || x[61] > 10.7600718f)) || (!isnan(x[62]) && (x[62] < -16.0f || x[62] > 78.936821f)) || (!isnan(x[63]) && (x[63] < 0.277918696f || x[63] > 35.6330299f)) || (!isnan(x[64]) && (x[64] < -1.0f || x[64] > 1.0f)) || (!isnan(x[65]) && (x[65] < -1.0f || x[65] > 1.0f)) || (!isnan(x[66]) && (x[66] < -1.0f || x[66] > 1.0f)) || (!isnan(x[67]) && (x[67] < -1.0f || x[67] > 1.0f)) || (!isnan(x[68]) && (x[68] < 0.0f || x[68] > 1.0f)) || (!isnan(x[69]) && (x[69] < 7.9833f || x[69] > 34.1359f)) || (!isnan(x[70]) && (x[70] < 68.85f || x[70] > 95.3833f)) || (!isnan(x[71]) && (x[71] < 0.0f || x[71] > 3258.0f))) status[1]=INDRA_OOD;
  else {
    raw[1]=indra_raw_1(x);
    float p=fminf(1.0f-1e-6f,fmaxf(1e-6f,raw[1]));
    prob[1]=1.0f/(1.0f+expf(-(1.86505044f*logf(p/(1-p))+1.19926929f)));
    status[1]=INDRA_ARCHIVE_CALIBRATED;
    flags[1]=(raw[1] >= 0.346421868f);
  }
  if ((!isnan(x[0]) && (x[0] < -16.0f || x[0] > 48.5f)) || (!isnan(x[1]) && (x[1] < 3.0f || x[1] > 100.0f)) || (!isnan(x[2]) && (x[2] < 499.700012f || x[2] > 1090.19995f)) || (!isnan(x[3]) && (x[3] < 0.0f || x[3] > 32.4000015f)) || (!isnan(x[4]) && (x[4] < -20.0f || x[4] > 46.5999985f)) || (!isnan(x[5]) && (x[5] < -16.0f || x[5] > 48.4000015f)) || (!isnan(x[6]) && (x[6] < -16.0f || x[6] > 48.5f)) || (!isnan(x[7]) && (x[7] < -14.0f || x[7] > 48.5f)) || (!isnan(x[8]) && (x[8] < -15.6000004f || x[8] > 48.5f)) || (!isnan(x[9]) && (x[9] < -13.75f || x[9] > 15.3999996f)) || (!isnan(x[10]) && (x[10] < -12.8500004f || x[10] > 45.5583344f)) || (!isnan(x[11]) && (x[11] < 0.0f || x[11] > 8.67187309f)) || (!isnan(x[12]) && (x[12] < 6.35208321f || x[12] > 40.0708351f)) || (!isnan(x[13]) && (x[13] < 0.122474484f || x[13] > 7.16749001f)) || (!isnan(x[14]) && (x[14] < 4.0f || x[14] > 100.0f)) || (!isnan(x[15]) && (x[15] < 4.0f || x[15] > 100.0f)) || (!isnan(x[16]) && (x[16] < 3.0f || x[16] > 100.0f)) || (!isnan(x[17]) && (x[17] < 3.0f || x[17] > 100.0f)) || (!isnan(x[18]) && (x[18] < 3.0f || x[18] > 100.0f)) || (!isnan(x[19]) && (x[19] < -60.0f || x[19] > 56.5f)) || (!isnan(x[20]) && (x[20] < 6.0f || x[20] > 100.0f)) || (!isnan(x[21]) && (x[21] < 0.0f || x[21] > 31.7227573f)) || (!isnan(x[22]) && (x[22] < 14.791667f || x[22] > 100.0f)) || (!isnan(x[23]) && (x[23] < 0.0f || x[23] > 35.2908974f)) || (!isnan(x[24]) && (x[24] < 647.700012f || x[24] > 1050.19995f)) || (!isnan(x[25]) && (x[25] < 499.700012f || x[25] > 1050.19995f)) || (!isnan(x[26]) && (x[26] < 499.700012f || x[26] > 1090.19995f)) || (!isnan(x[27]) && (x[27] < 499.700012f || x[27] > 1090.19995f)) || (!isnan(x[28]) && (x[28] < 499.700012f || x[28] > 1090.19995f)) || (!isnan(x[29]) && (x[29] < -1.79999995f || x[29] > -1.5f)) || (!isnan(x[30]) && (x[30] < 0.0f || x[30] > 32.4000015f)) || (!isnan(x[31]) && (x[31] < 0.0f || x[31] > 38.0999985f)) || (!isnan(x[32]) && (x[32] < 0.0f || x[32] > 38.0999985f)) || (!isnan(x[33]) && (x[33] < 0.0f || x[33] > 38.0999985f)) || (!isnan(x[34]) && (x[34] < 0.0f || x[34] > 38.0999985f)) || (!isnan(x[35]) && (x[35] < -28.7999992f || x[35] > 12.6000004f)) || (!isnan(x[36]) && (x[36] < 0.0f || x[36] > 13.1333332f)) || (!isnan(x[37]) && (x[37] < 0.0f || x[37] > 11.3375483f)) || (!isnan(x[38]) && (x[38] < 0.0f || x[38] > 7.76041651f)) || (!isnan(x[39]) && (x[39] < 0.0f || x[39] > 3.96652436f)) || (!isnan(x[40]) && (x[40] < -17.3500004f || x[40] > 24.0f)) || (!isnan(x[41]) && (x[41] < -17.5f || x[41] > 45.0f)) || (!isnan(x[42]) && (x[42] < -7.0f || x[42] > 46.5999985f)) || (!isnan(x[43]) && (x[43] < -81.5f || x[43] > 82.5f)) || (!isnan(x[44]) && (x[44] < 4.0f || x[44] > 100.0f)) || (!isnan(x[45]) && (x[45] < 7.5f || x[45] > 100.0f)) || (!isnan(x[46]) && (x[46] < -29.7999992f || x[46] > 14.8999996f)) || (!isnan(x[47]) && (x[47] < 0.0f || x[47] > 11.8500004f)) || (!isnan(x[48]) && (x[48] < 0.0f || x[48] > 32.4000015f)) || (!isnan(x[49]) && (x[49] < -19.5f || x[49] > 13.3500004f)) || (!isnan(x[50]) && (x[50] < 1.70000005f || x[50] > 35.75f)) || (!isnan(x[51]) && (x[51] < 8.80000019f || x[51] > 46.5999985f)) || (!isnan(x[52]) && (x[52] < -64.0f || x[52] > 69.5f)) || (!isnan(x[53]) && (x[53] < 6.0f || x[53] > 100.0f)) || (!isnan(x[54]) && (x[54] < 22.5f || x[54] > 100.0f)) || (!isnan(x[55]) && (x[55] < -15.1999998f || x[55] > 13.6000004f)) || (!isnan(x[56]) && (x[56] < 0.0f || x[56] > 6.19999981f)) || (!isnan(x[57]) && (x[57] < 0.0f || x[57] > 17.5f)) || (!isnan(x[58]) && (x[58] < -0.0299999993f || x[58] > -0.0250000004f)) || (!isnan(x[59]) && (x[59] < -33.8489342f || x[59] > 33.7245483f)) || (!isnan(x[60]) && (x[60] < -7.10542736e-15f || x[60] > 53.9953384f)) || (!isnan(x[61]) && (x[61] < 0.0f || x[61] > 10.7600718f)) || (!isnan(x[62]) && (x[62] < -16.0f || x[62] > 78.936821f)) || (!isnan(x[63]) && (x[63] < 0.277918696f || x[63] > 35.6330299f)) || (!isnan(x[64]) && (x[64] < -1.0f || x[64] > 1.0f)) || (!isnan(x[65]) && (x[65] < -1.0f || x[65] > 1.0f)) || (!isnan(x[66]) && (x[66] < -1.0f || x[66] > 1.0f)) || (!isnan(x[67]) && (x[67] < -1.0f || x[67] > 1.0f)) || (!isnan(x[68]) && (x[68] < 0.0f || x[68] > 1.0f)) || (!isnan(x[69]) && (x[69] < 7.9833f || x[69] > 34.1359f)) || (!isnan(x[70]) && (x[70] < 68.85f || x[70] > 95.3833f)) || (!isnan(x[71]) && (x[71] < 0.0f || x[71] > 3258.0f))) status[2]=INDRA_OOD;
  else {
    raw[2]=indra_raw_2(x);
    float p=fminf(1.0f-1e-6f,fmaxf(1e-6f,raw[2]));
    prob[2]=1.0f/(1.0f+expf(-(1.05783308f*logf(p/(1-p))+-1.30908668f)));
    status[2]=INDRA_ARCHIVE_CALIBRATED;
    flags[2]=(raw[2] >= 0.803102493f);
  }
  return 1;
}
#endif
