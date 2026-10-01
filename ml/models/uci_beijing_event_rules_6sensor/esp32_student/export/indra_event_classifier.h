/* Sensor-rule classifier. No independently observed hazard labels. */
#ifndef INDRA_EVENT_CLASSIFIER_H
#define INDRA_EVENT_CLASSIFIER_H
#include <math.h>
#include <stddef.h>
#define INDRA_EVENT_INPUTS 17
#define INDRA_EVENT_OUTPUTS 12
#define INDRA_EVENT_STATUS "OFFLINE_RESEARCH_ONLY"
/* Input feature order: temperature_c, relative_humidity_pct, pressure_hpa, pm25_ug_m3, pm10_ug_m3, wind_speed_mps, T_dew, VPD, HI, PM_ratio, dP_dt, dP_6h, dT_dt, dPM25_dt, dPM10_dt, dRH_dt, pm25_mono_6h */
/* Output probability order: light_moderate_rain, severe_rainstorm_squall, snowstorm_blizzard, freezing_rain_sleet, radiation_fog, ground_frost, extreme_heatwave, wildfire_evaporative_risk, dust_storm_haboob, smoke_plume, smog_inversion_trap, cold_frontal_passage */
static inline float indra_ev_0_0(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0999922007f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[14] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0980198011f;
        } else {
          return 0.0996427387f;
        }
      } else {
        return -0.0993880704f;
      }
    } else {
      return -0.0999556184f;
    }
  }
}
static inline float indra_ev_0_1(const float *x) {
  if (x[11] < -1.39999998f) {
    if (x[7] < 0.500933349f) {
      if (x[6] < 1.29999995f) {
        return -0.0951318666f;
      } else {
        if (x[13] < 0.100000001f) {
          return 0.0940133557f;
        } else {
          return -0.0960306376f;
        }
      }
    } else {
      if (x[6] < 23.6000004f) {
        return -0.0952078104f;
      } else {
        if (x[7] < 0.596009493f) {
          return 0.091363363f;
        } else {
          return -0.0936239883f;
        }
      }
    }
  } else {
    return -0.095234178f;
  }
}
static inline float indra_ev_0_2(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0911780968f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[14] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0897988155f;
        } else {
          return 0.0908615217f;
        }
      } else {
        return -0.0917947367f;
      }
    } else {
      return -0.0910929069f;
    }
  }
}
static inline float indra_ev_0_3(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0875877291f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[13] < 0.100000001f) {
        if (x[8] < 3.0999999f) {
          return -0.086407356f;
        } else {
          return 0.087341778f;
        }
      } else {
        return -0.0898900703f;
      }
    } else {
      return -0.0875129029f;
    }
  }
}
static inline float indra_ev_0_4(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0844366476f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[13] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0832909644f;
        } else {
          return 0.0841816589f;
        }
      } else {
        return -0.086404115f;
      }
    } else {
      return -0.0843671858f;
    }
  }
}
static inline float indra_ev_0_5(const float *x) {
  if (x[11] < -1.39999998f) {
    if (x[7] < 0.500933349f) {
      if (x[6] < 1.29999995f) {
        return -0.0815136358f;
      } else {
        if (x[13] < 0.100000001f) {
          return 0.0805028826f;
        } else {
          return -0.0830091611f;
        }
      }
    } else {
      if (x[6] < 24.7999992f) {
        if (x[7] < 0.510888875f) {
          return -0.0247483365f;
        } else {
          return -0.081588462f;
        }
      } else {
        if (x[7] < 0.596009493f) {
          return 0.0796748921f;
        } else {
          return -0.0776435286f;
        }
      }
    }
  } else {
    return -0.0816079304f;
  }
}
static inline float indra_ev_0_6(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0792100653f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[14] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.078357406f;
        } else {
          return 0.078916274f;
        }
      } else {
        if (x[13] < 0.100000001f) {
          return -0.0994645879f;
        } else {
          return -0.0783580244f;
        }
      }
    } else {
      return -0.0791062936f;
    }
  }
}
static inline float indra_ev_0_7(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.076987274f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[13] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0761381313f;
        } else {
          return 0.0767265782f;
        }
      } else {
        return -0.0796242282f;
      }
    } else {
      return -0.0768898875f;
    }
  }
}
static inline float indra_ev_0_8(const float *x) {
  if (x[11] < -1.39999998f) {
    if (x[14] < 0.100000001f) {
      if (x[6] < 1.29999995f) {
        return -0.0748531818f;
      } else {
        if (x[0] < 28.7000008f) {
          return 0.0697352737f;
        } else {
          return -0.0653916001f;
        }
      }
    } else {
      return -0.0753686205f;
    }
  } else {
    return -0.0749178305f;
  }
}
static inline float indra_ev_0_9(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0733508095f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[14] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.072526671f;
        } else {
          return 0.07300248f;
        }
      } else {
        return -0.0771268159f;
      }
    } else {
      return -0.0730972961f;
    }
  }
}
static inline float indra_ev_0_10(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0717008933f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[13] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0709732398f;
        } else {
          return 0.0714143962f;
        }
      } else {
        if (x[14] < 0.100000001f) {
          return -0.0921945497f;
        } else {
          return -0.070632048f;
        }
      }
    } else {
      return -0.0714662448f;
    }
  }
}
static inline float indra_ev_0_11(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0701996014f;
  } else {
    if (x[0] < 3.0999999f) {
      return -0.0699047074f;
    } else {
      if (x[10] < -0.100000001f) {
        if (x[16] < 1.0f) {
          return 0.0633575842f;
        } else {
          return -0.0672680289f;
        }
      } else {
        if (x[9] < 0.800000012f) {
          return 0.00774618192f;
        } else {
          return 0.0417557284f;
        }
      }
    }
  }
}
static inline float indra_ev_0_12(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0688309595f;
  } else {
    if (x[13] < 0.100000001f) {
      if (x[14] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0684532076f;
        } else {
          return 0.0618930347f;
        }
      } else {
        return -0.0741767585f;
      }
    } else {
      return -0.0710585937f;
    }
  }
}
static inline float indra_ev_0_13(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0675804093f;
  } else {
    if (x[13] < 0.100000001f) {
      if (x[14] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0672291666f;
        } else {
          return 0.0604510978f;
        }
      } else {
        return -0.072622411f;
      }
    } else {
      return -0.0695973933f;
    }
  }
}
static inline float indra_ev_0_14(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0664321855f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[13] < 0.100000001f) {
        if (x[14] < 0.100000001f) {
          return 0.0665492192f;
        } else {
          return -0.0899448916f;
        }
      } else {
        if (x[14] < 0.100000001f) {
          return -0.085030064f;
        } else {
          return -0.0667979643f;
        }
      }
    } else {
      if (x[13] < 0.100000001f) {
        return -0.0717592165f;
      } else {
        return -0.0677469596f;
      }
    }
  }
}
static inline float indra_ev_0_15(const float *x) {
  if (x[1] < 84.9953308f) {
    return -0.0653768554f;
  } else {
    if (x[11] < -1.39999998f) {
      if (x[13] < 0.100000001f) {
        if (x[0] < 3.0999999f) {
          return -0.0663307831f;
        } else {
          return 0.0655016601f;
        }
      } else {
        if (x[14] < 0.100000001f) {
          return -0.0819830894f;
        } else {
          return -0.0656183884f;
        }
      }
    } else {
      if (x[13] < 0.100000001f) {
        return -0.0702494904f;
      } else {
        return -0.0665861294f;
      }
    }
  }
}
static inline float indra_ev_head_0(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_0_0(x);
  raw += indra_ev_0_1(x);
  raw += indra_ev_0_2(x);
  raw += indra_ev_0_3(x);
  raw += indra_ev_0_4(x);
  raw += indra_ev_0_5(x);
  raw += indra_ev_0_6(x);
  raw += indra_ev_0_7(x);
  raw += indra_ev_0_8(x);
  raw += indra_ev_0_9(x);
  raw += indra_ev_0_10(x);
  raw += indra_ev_0_11(x);
  raw += indra_ev_0_12(x);
  raw += indra_ev_0_13(x);
  raw += indra_ev_0_14(x);
  raw += indra_ev_0_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_head_1(const float *x) { (void)x; return 0.0f; }
static inline float indra_ev_head_2(const float *x) { (void)x; return 0.0f; }
static inline float indra_ev_3_0(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[0] < -2.0f) {
        return -0.0992167145f;
      } else {
        if (x[11] < 3.5f) {
          return 0.0993942469f;
        } else {
          return 0.0871945545f;
        }
      }
    } else {
      return -0.0998027921f;
    }
  } else {
    return -0.0999931917f;
  }
}
static inline float indra_ev_3_1(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0935222059f;
        } else {
          return 0.0952485576f;
        }
      } else {
        return -0.0986668542f;
      }
    } else {
      return -0.0950633511f;
    }
  } else {
    return -0.0952356905f;
  }
}
static inline float indra_ev_3_2(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0895351321f;
        } else {
          return 0.0911380127f;
        }
      } else {
        return -0.0939441845f;
      }
    } else {
      return -0.0909660459f;
    }
  } else {
    return -0.0911260471f;
  }
}
static inline float indra_ev_3_3(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[8] < 0.600000024f) {
      if (x[8] < -2.0f) {
        return -0.0867926702f;
      } else {
        if (x[11] < 3.5f) {
          return 0.0870227888f;
        } else {
          return 0.0761677548f;
        }
      }
    } else {
      return -0.087395601f;
    }
  } else {
    return -0.087543726f;
  }
}
static inline float indra_ev_3_4(const float *x) {
  if (x[1] < 89.9848022f) {
    return -0.084399946f;
  } else {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0817501023f;
        } else {
          return 0.0844381899f;
        }
      } else {
        return -0.0913847163f;
      }
    } else {
      return -0.0843529552f;
    }
  }
}
static inline float indra_ev_3_5(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[8] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[8] < -2.0f) {
          return -0.0802499354f;
        } else {
          return 0.0816358849f;
        }
      } else {
        return -0.0865895227f;
      }
    } else {
      return -0.0814721286f;
    }
  } else {
    return -0.0816121846f;
  }
}
static inline float indra_ev_3_6(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0777676329f;
        } else {
          return 0.0791500136f;
        }
      } else {
        return -0.0835048407f;
      }
    } else {
      return -0.0789987072f;
    }
  } else {
    return -0.0791343078f;
  }
}
static inline float indra_ev_3_7(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0756269023f;
        } else {
          return 0.0769308582f;
        }
      } else {
        return -0.0807834342f;
      }
    } else {
      return -0.0767844468f;
    }
  } else {
    return -0.0769172534f;
  }
}
static inline float indra_ev_3_8(const float *x) {
  if (x[0] < 0.600000024f) {
    if (x[6] < -3.4000001f) {
      return -0.0748870596f;
    } else {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0650379881f;
        } else {
          return 0.0746480674f;
        }
      } else {
        return -0.0798016042f;
      }
    }
  } else {
    return -0.0749244988f;
  }
}
static inline float indra_ev_3_9(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0718682483f;
        } else {
          return 0.0731422156f;
        }
      } else {
        return -0.0763418823f;
      }
    } else {
      return -0.0729911402f;
    }
  } else {
    return -0.0731320903f;
  }
}
static inline float indra_ev_3_10(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0702287555f;
        } else {
          return 0.0715117231f;
        }
      } else {
        return -0.0744603872f;
      }
    } else {
      return -0.071359694f;
    }
  } else {
    return -0.0715005919f;
  }
}
static inline float indra_ev_3_11(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0687693805f;
        } else {
          return 0.0700190291f;
        }
      } else {
        return -0.0726134032f;
      }
    } else {
      return -0.0698752627f;
    }
  } else {
    return -0.0700160637f;
  }
}
static inline float indra_ev_3_12(const float *x) {
  if (x[1] < 89.9848022f) {
    return -0.0686698928f;
  } else {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0663208812f;
        } else {
          return 0.0686828941f;
        }
      } else {
        return -0.0716575235f;
      }
    } else {
      return -0.068615362f;
    }
  }
}
static inline float indra_ev_3_13(const float *x) {
  if (x[1] < 89.9848022f) {
    return -0.0674318075f;
  } else {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0650906116f;
        } else {
          return 0.0674412623f;
        }
      } else {
        return -0.0701273531f;
      }
    } else {
      return -0.0673763454f;
    }
  }
}
static inline float indra_ev_3_14(const float *x) {
  if (x[7] < 0.0615019985f) {
    if (x[0] < 0.600000024f) {
      if (x[0] < -2.0f) {
        return -0.0654025301f;
      } else {
        if (x[11] < 2.5f) {
          return 0.0658547804f;
        } else {
          return 0.0590103939f;
        }
      }
    } else {
      return -0.0661387891f;
    }
  } else {
    return -0.0662868842f;
  }
}
static inline float indra_ev_3_15(const float *x) {
  if (x[1] < 89.9848022f) {
    return -0.0652507097f;
  } else {
    if (x[0] < 0.600000024f) {
      if (x[10] < 0.0f) {
        if (x[0] < -2.0f) {
          return -0.0628146678f;
        } else {
          return 0.0652668923f;
        }
      } else {
        return -0.0692187771f;
      }
    } else {
      return -0.0651938915f;
    }
  }
}
static inline float indra_ev_head_3(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_3_0(x);
  raw += indra_ev_3_1(x);
  raw += indra_ev_3_2(x);
  raw += indra_ev_3_3(x);
  raw += indra_ev_3_4(x);
  raw += indra_ev_3_5(x);
  raw += indra_ev_3_6(x);
  raw += indra_ev_3_7(x);
  raw += indra_ev_3_8(x);
  raw += indra_ev_3_9(x);
  raw += indra_ev_3_10(x);
  raw += indra_ev_3_11(x);
  raw += indra_ev_3_12(x);
  raw += indra_ev_3_13(x);
  raw += indra_ev_3_14(x);
  raw += indra_ev_3_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_4_0(const float *x) {
  if (x[1] < 94.7199631f) {
    return -0.0999931395f;
  } else {
    if (x[3] < 80.5f) {
      return -0.0997387394f;
    } else {
      if (x[5] < 1.5f) {
        if (x[1] < 95.0249786f) {
          return 0.0334710479f;
        } else {
          return 0.0999932736f;
        }
      } else {
        return -0.0975659266f;
      }
    }
  }
}
static inline float indra_ev_4_1(const float *x) {
  if (x[7] < 0.140126556f) {
    if (x[4] < 58.0f) {
      if (x[9] < 1.5f) {
        if (x[9] < 1.41025639f) {
          return -0.0950122178f;
        } else {
          return -0.0219323467f;
        }
      } else {
        if (x[4] < 20.7999992f) {
          return -0.0202436969f;
        } else {
          return 0.0679110885f;
        }
      }
    } else {
      if (x[6] < -4.5999999f) {
        if (x[7] < 0.0244289655f) {
          return 0.088481985f;
        } else {
          return -0.0949298218f;
        }
      } else {
        if (x[5] < 1.5f) {
          return 0.0874426961f;
        } else {
          return -0.0945388004f;
        }
      }
    }
  } else {
    if (x[6] < 25.6000004f) {
      return -0.0952383801f;
    } else {
      if (x[7] < 0.160953715f) {
        return 0.0930021107f;
      } else {
        return -0.0936908647f;
      }
    }
  }
}
static inline float indra_ev_4_2(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[7] < 0.140126556f) {
      return -0.0950011536f;
    } else {
      return -0.0911256149f;
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0935581774f;
    } else {
      if (x[5] < 1.5f) {
        if (x[1] < 95.0249786f) {
          return 0.0319563001f;
        } else {
          return 0.0914605409f;
        }
      } else {
        return -0.0896956548f;
      }
    }
  }
}
static inline float indra_ev_4_3(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[7] < 0.140126556f) {
      return -0.0909719169f;
    } else {
      return -0.087543346f;
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0896882042f;
    } else {
      if (x[5] < 1.5f) {
        if (x[1] < 95.0249786f) {
          return 0.0297293663f;
        } else {
          return 0.0878393576f;
        }
      } else {
        return -0.0861954167f;
      }
    }
  }
}
static inline float indra_ev_4_4(const float *x) {
  if (x[1] < 94.7199631f) {
    return -0.0846344084f;
  } else {
    if (x[3] < 80.5f) {
      return -0.0862698629f;
    } else {
      if (x[5] < 1.5f) {
        if (x[1] < 95.0249786f) {
          return 0.0269056801f;
        } else {
          return 0.0846551061f;
        }
      } else {
        return -0.0830142722f;
      }
    }
  }
}
static inline float indra_ev_4_5(const float *x) {
  if (x[7] < 0.140126556f) {
    if (x[3] < 80.5f) {
      return -0.0832771361f;
    } else {
      if (x[6] < -4.5999999f) {
        if (x[7] < 0.0244289655f) {
          return 0.0752106011f;
        } else {
          return -0.0810868442f;
        }
      } else {
        if (x[7] < 0.0661184117f) {
          return 0.0797039047f;
        } else {
          return 0.0645902082f;
        }
      }
    }
  } else {
    if (x[6] < 25.6000004f) {
      return -0.0816143677f;
    } else {
      if (x[7] < 0.160953715f) {
        return 0.0796453878f;
      } else {
        return -0.0805104598f;
      }
    }
  }
}
static inline float indra_ev_4_6(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[7] < 0.140126556f) {
      if (x[6] < -4.5999999f) {
        return -0.0787766129f;
      } else {
        if (x[3] < 80.5f) {
          return -0.0807235464f;
        } else {
          return -0.0892630517f;
        }
      }
    } else {
      return -0.0791270658f;
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0805858076f;
    } else {
      if (x[1] < 95.0249786f) {
        if (x[6] < 15.1000004f) {
          return -0.0464964025f;
        } else {
          return 0.0605739467f;
        }
      } else {
        if (x[12] < -4.80000019f) {
          return 0.0296947062f;
        } else {
          return 0.0790856704f;
        }
      }
    }
  }
}
static inline float indra_ev_4_7(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[7] < 0.140126556f) {
      if (x[6] < -4.5999999f) {
        return -0.0765813217f;
      } else {
        if (x[3] < 80.5f) {
          return -0.0783374831f;
        } else {
          return -0.0858770236f;
        }
      }
    } else {
      return -0.0769107044f;
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0782218203f;
    } else {
      if (x[5] < 1.5f) {
        if (x[1] < 95.0249786f) {
          return 0.0197308995f;
        } else {
          return 0.0772731528f;
        }
      } else {
        return -0.0852152035f;
      }
    }
  }
}
static inline float indra_ev_4_8(const float *x) {
  if (x[3] < 81.0f) {
    return -0.0750184208f;
  } else {
    if (x[5] < 1.5f) {
      if (x[6] < -4.5999999f) {
        if (x[6] < -6.30000019f) {
          return -0.0748006478f;
        } else {
          return -0.0202637557f;
        }
      } else {
        if (x[0] < 25.3999996f) {
          return 0.0546686836f;
        } else {
          return -0.0180362985f;
        }
      }
    } else {
      return -0.0751986727f;
    }
  }
}
static inline float indra_ev_4_9(const float *x) {
  if (x[1] < 95.0249786f) {
    if (x[1] < 94.7199631f) {
      if (x[7] < 0.140126556f) {
        if (x[6] < -4.5999999f) {
          return -0.0731424838f;
        } else {
          return -0.0812026858f;
        }
      } else {
        return -0.0736167282f;
      }
    } else {
      if (x[6] < 15.1000004f) {
        if (x[2] < 1019.40002f) {
          return -0.097056739f;
        } else {
          return 0.0109508811f;
        }
      } else {
        if (x[0] < 16.5f) {
          return 0.0780350491f;
        } else {
          return -0.0845594779f;
        }
      }
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0741998255f;
    } else {
      if (x[5] < 1.5f) {
        return 0.0739507899f;
      } else {
        return -0.0798779353f;
      }
    }
  }
}
static inline float indra_ev_4_10(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[7] < 0.140126556f) {
      if (x[6] < -4.5999999f) {
        return -0.0714831874f;
      } else {
        if (x[3] < 80.5f) {
          return -0.0723618791f;
        } else {
          return -0.0816711411f;
        }
      }
    } else {
      return -0.0719416887f;
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0724473819f;
    } else {
      if (x[1] < 95.0249786f) {
        if (x[6] < 15.1000004f) {
          return -0.0541289821f;
        } else {
          return 0.0527434051f;
        }
      } else {
        if (x[12] < -3.4000001f) {
          return 0.0346606448f;
        } else {
          return 0.0718358234f;
        }
      }
    }
  }
}
static inline float indra_ev_4_11(const float *x) {
  if (x[1] < 95.0249786f) {
    if (x[1] < 94.7199631f) {
      if (x[7] < 0.140126556f) {
        if (x[6] < -4.5999999f) {
          return -0.0699848533f;
        } else {
          return -0.0766631514f;
        }
      } else {
        return -0.0704191402f;
      }
    } else {
      if (x[6] < 15.1000004f) {
        if (x[2] < 1019.0f) {
          return -0.0911660269f;
        } else {
          return 0.0139050931f;
        }
      } else {
        if (x[0] < 16.5f) {
          return 0.0743437111f;
        } else {
          return -0.0832396671f;
        }
      }
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0708703622f;
    } else {
      if (x[5] < 1.5f) {
        return 0.0707049295f;
      } else {
        return -0.0796427205f;
      }
    }
  }
}
static inline float indra_ev_4_12(const float *x) {
  if (x[1] < 95.0249786f) {
    if (x[1] < 94.7199631f) {
      if (x[1] < 80.2241974f) {
        return -0.068964988f;
      } else {
        if (x[0] < 8.69999981f) {
          return -0.0736541674f;
        } else {
          return -0.0699618235f;
        }
      }
    } else {
      if (x[6] < 15.1000004f) {
        if (x[2] < 1019.40002f) {
          return -0.0878747031f;
        } else {
          return -0.00349770742f;
        }
      } else {
        if (x[2] < 1006.0f) {
          return -0.0815212354f;
        } else {
          return 0.0734959617f;
        }
      }
    }
  } else {
    if (x[4] < 47.0f) {
      if (x[9] < 1.83333337f) {
        return -0.0681708977f;
      } else {
        if (x[4] < 20.7999992f) {
          return -0.00501423096f;
        } else {
          return 0.0553254671f;
        }
      }
    } else {
      if (x[5] < 1.5f) {
        if (x[4] < 81.0f) {
          return 0.0495307595f;
        } else {
          return 0.0689764246f;
        }
      } else {
        return -0.0746599361f;
      }
    }
  }
}
static inline float indra_ev_4_13(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[3] < 80.5f) {
      return -0.0674015507f;
    } else {
      if (x[1] < 80.2241974f) {
        return -0.0682485104f;
      } else {
        return -0.0712292939f;
      }
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.069220379f;
    } else {
      if (x[5] < 1.5f) {
        if (x[1] < 95.0249786f) {
          return 0.0158662591f;
        } else {
          return 0.0680219159f;
        }
      } else {
        return -0.0751700625f;
      }
    }
  }
}
static inline float indra_ev_4_14(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[7] < 0.140126556f) {
      if (x[6] < -4.5999999f) {
        return -0.0661480427f;
      } else {
        if (x[3] < 80.5f) {
          return -0.066676423f;
        } else {
          return -0.0734031275f;
        }
      }
    } else {
      return -0.0665951595f;
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0679123327f;
    } else {
      if (x[1] < 95.0249786f) {
        if (x[6] < 15.1000004f) {
          return -0.036249958f;
        } else {
          return 0.0467485264f;
        }
      } else {
        if (x[12] < -3.4000001f) {
          return 0.0308552142f;
        } else {
          return 0.0664325282f;
        }
      }
    }
  }
}
static inline float indra_ev_4_15(const float *x) {
  if (x[1] < 94.7199631f) {
    if (x[3] < 80.5f) {
      return -0.0652183294f;
    } else {
      if (x[1] < 80.2241974f) {
        return -0.0659459084f;
      } else {
        return -0.0684685037f;
      }
    }
  } else {
    if (x[3] < 80.5f) {
      return -0.0667197257f;
    } else {
      if (x[1] < 95.0249786f) {
        if (x[6] < 15.1000004f) {
          return -0.0341486707f;
        } else {
          return 0.0481624007f;
        }
      } else {
        if (x[12] < -3.4000001f) {
          return 0.0308510456f;
        } else {
          return 0.0653080866f;
        }
      }
    }
  }
}
static inline float indra_ev_head_4(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_4_0(x);
  raw += indra_ev_4_1(x);
  raw += indra_ev_4_2(x);
  raw += indra_ev_4_3(x);
  raw += indra_ev_4_4(x);
  raw += indra_ev_4_5(x);
  raw += indra_ev_4_6(x);
  raw += indra_ev_4_7(x);
  raw += indra_ev_4_8(x);
  raw += indra_ev_4_9(x);
  raw += indra_ev_4_10(x);
  raw += indra_ev_4_11(x);
  raw += indra_ev_4_12(x);
  raw += indra_ev_4_13(x);
  raw += indra_ev_4_14(x);
  raw += indra_ev_4_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_5_0(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[5] < 2.0f) {
      if (x[11] < -0.349999994f) {
        if (x[11] < -2.0f) {
          return 0.0735853761f;
        } else {
          return 0.0839995965f;
        }
      } else {
        if (x[11] < 1.10000002f) {
          return 0.0920946747f;
        } else {
          return 0.097528927f;
        }
      }
    } else {
      return -0.099769406f;
    }
  } else {
    return -0.0999925137f;
  }
}
static inline float indra_ev_5_1(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      if (x[5] < 2.0f) {
        return -0.104274549f;
      } else {
        return -0.0946793854f;
      }
    } else {
      if (x[5] < 2.0f) {
        return 0.0956209227f;
      } else {
        return -0.0949023291f;
      }
    }
  } else {
    return -0.0952350721f;
  }
}
static inline float indra_ev_5_2(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0973732397f;
    } else {
      if (x[5] < 2.0f) {
        return 0.0914600417f;
      } else {
        return -0.0908153877f;
      }
    }
  } else {
    return -0.0911254734f;
  }
}
static inline float indra_ev_5_3(const float *x) {
  if (x[8] < 0.100000001f) {
    if (x[5] < 2.0f) {
      if (x[11] < -0.200000003f) {
        if (x[11] < -1.66666698f) {
          return 0.0654396713f;
        } else {
          return 0.0746039823f;
        }
      } else {
        if (x[11] < 1.10000002f) {
          return 0.0805909261f;
        } else {
          return 0.085349068f;
        }
      }
    } else {
      return -0.0872875154f;
    }
  } else {
    return -0.0875431895f;
  }
}
static inline float indra_ev_5_4(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      if (x[5] < 2.0f) {
        return -0.0977746695f;
      } else {
        return -0.0836957023f;
      }
    } else {
      if (x[5] < 2.0f) {
        return 0.0849339813f;
      } else {
        return -0.0841158256f;
      }
    }
  } else {
    return -0.084395878f;
  }
}
static inline float indra_ev_5_5(const float *x) {
  if (x[8] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0910723284f;
    } else {
      if (x[9] < 0.264150947f) {
        if (x[7] < 0.426029861f) {
          return 0.0568006709f;
        } else {
          return 0.00367861055f;
        }
      } else {
        if (x[3] < 14.3000002f) {
          return 0.0699280649f;
        } else {
          return 0.0810967013f;
        }
      }
    }
  } else {
    return -0.0816117078f;
  }
}
static inline float indra_ev_5_6(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0874817967f;
    } else {
      if (x[9] < 0.206896558f) {
        if (x[1] < 25.905859f) {
          return 0.00651098369f;
        } else {
          return 0.0618544891f;
        }
      } else {
        if (x[3] < 14.3000002f) {
          return 0.0664717183f;
        } else {
          return 0.078541778f;
        }
      }
    }
  } else {
    return -0.0791338384f;
  }
}
static inline float indra_ev_5_7(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      if (x[5] < 2.0f) {
        return -0.0862130895f;
      } else {
        return -0.075818859f;
      }
    } else {
      if (x[5] < 2.0f) {
        return 0.0774453282f;
      } else {
        return -0.0855022073f;
      }
    }
  } else {
    return -0.0769167915f;
  }
}
static inline float indra_ev_5_8(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      if (x[5] < 2.0f) {
        return -0.0832182467f;
      } else {
        return -0.0738958493f;
      }
    } else {
      if (x[5] < 2.0f) {
        return 0.075403899f;
      } else {
        return -0.082556501f;
      }
    }
  } else {
    return -0.0749236047f;
  }
}
static inline float indra_ev_5_9(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      if (x[5] < 2.0f) {
        return -0.0805559829f;
      } else {
        return -0.0721543729f;
      }
    } else {
      if (x[5] < 2.0f) {
        return 0.0735613257f;
      } else {
        return -0.0799387693f;
      }
    }
  } else {
    return -0.0731240138f;
  }
}
static inline float indra_ev_5_10(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0768929124f;
    } else {
      if (x[1] < 26.8845081f) {
        if (x[4] < 319.0f) {
          return 0.0541621149f;
        } else {
          return -0.0439693257f;
        }
      } else {
        if (x[3] < 10.6999998f) {
          return 0.0598996989f;
        } else {
          return 0.0708760545f;
        }
      }
    }
  } else {
    return -0.0714929402f;
  }
}
static inline float indra_ev_5_11(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0749117583f;
    } else {
      if (x[5] < 2.0f) {
        return 0.0704250112f;
      } else {
        return -0.0793186873f;
      }
    }
  } else {
    return -0.0700094998f;
  }
}
static inline float indra_ev_5_12(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0731050968f;
    } else {
      if (x[5] < 2.0f) {
        return 0.0690365732f;
      } else {
        return -0.0770709887f;
      }
    }
  } else {
    return -0.0686560571f;
  }
}
static inline float indra_ev_5_13(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0714834407f;
    } else {
      if (x[5] < 2.0f) {
        return 0.0677647665f;
      } else {
        return -0.0750529096f;
      }
    }
  } else {
    return -0.0674176589f;
  }
}
static inline float indra_ev_5_14(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[1] < 26.8845081f) {
      if (x[9] < 0.272727281f) {
        if (x[12] < -0.366666675f) {
          return 0.015253081f;
        } else {
          return -0.0244671833f;
        }
      } else {
        if (x[15] < 1.97506022f) {
          return 0.0386472121f;
        } else {
          return 0.0551590919f;
        }
      }
    } else {
      if (x[11] < -0.5f) {
        if (x[11] < -4.0f) {
          return 0.0328616388f;
        } else {
          return 0.0507435277f;
        }
      } else {
        if (x[3] < 10.6999998f) {
          return 0.0469940566f;
        } else {
          return 0.0612819195f;
        }
      }
    }
  } else {
    return -0.0662815794f;
  }
}
static inline float indra_ev_5_15(const float *x) {
  if (x[0] < 0.100000001f) {
    if (x[10] < 0.0f) {
      return -0.0710266754f;
    } else {
      if (x[9] < 0.196078435f) {
        if (x[1] < 27.9903564f) {
          return 0.00519075198f;
        } else {
          return 0.0542725287f;
        }
      } else {
        if (x[3] < 14.3000002f) {
          return 0.0530639291f;
        } else {
          return 0.0645056441f;
        }
      }
    }
  } else {
    return -0.0652368441f;
  }
}
static inline float indra_ev_head_5(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_5_0(x);
  raw += indra_ev_5_1(x);
  raw += indra_ev_5_2(x);
  raw += indra_ev_5_3(x);
  raw += indra_ev_5_4(x);
  raw += indra_ev_5_5(x);
  raw += indra_ev_5_6(x);
  raw += indra_ev_5_7(x);
  raw += indra_ev_5_8(x);
  raw += indra_ev_5_9(x);
  raw += indra_ev_5_10(x);
  raw += indra_ev_5_11(x);
  raw += indra_ev_5_12(x);
  raw += indra_ev_5_13(x);
  raw += indra_ev_5_14(x);
  raw += indra_ev_5_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_6_0(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.0999932215f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0991228074f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0997388512f;
        } else {
          return 0.0984394178f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0954150781f;
        } else {
          return 0.0999905244f;
        }
      }
    }
  }
}
static inline float indra_ev_6_1(const float *x) {
  if (x[0] < 30.6000004f) {
    if (x[6] < 25.6000004f) {
      return -0.0952358916f;
    } else {
      if (x[0] < 30.0f) {
        return -0.0925440043f;
      } else {
        if (x[7] < 0.478162766f) {
          return 0.0944610015f;
        } else {
          return -0.0794019923f;
        }
      }
    }
  } else {
    if (x[0] < 34.2999992f) {
      if (x[6] < 24.2000008f) {
        return -0.0952037126f;
      } else {
        if (x[6] < 24.7999992f) {
          return 0.0773824379f;
        } else {
          return 0.0939593092f;
        }
      }
    } else {
      if (x[0] < 35.2000008f) {
        if (x[2] < 1003.70001f) {
          return 0.0908732712f;
        } else {
          return 0.0517707244f;
        }
      } else {
        return 0.0952330008f;
      }
    }
  }
}
static inline float indra_ev_6_2(const float *x) {
  if (x[8] < 32.6142845f) {
    if (x[0] < 34.2999992f) {
      return -0.0911262557f;
    } else {
      if (x[1] < 11.9616098f) {
        return 0.0892196298f;
      } else {
        return -0.0852421746f;
      }
    }
  } else {
    if (x[0] < 30.0f) {
      return -0.0902298838f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0913530067f;
        } else {
          return 0.0896450803f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0870589092f;
        } else {
          return 0.0911235064f;
        }
      }
    }
  }
}
static inline float indra_ev_6_3(const float *x) {
  if (x[8] < 32.6142845f) {
    if (x[7] < 4.16863966f) {
      return -0.0875440165f;
    } else {
      if (x[11] < -5.0999999f) {
        if (x[3] < 70.6999969f) {
          return 0.0594662242f;
        } else {
          return 0.0868616104f;
        }
      } else {
        return -0.0857167691f;
      }
    }
  } else {
    if (x[8] < 33.3625374f) {
      if (x[1] < 21.0079517f) {
        return 0.0868473276f;
      } else {
        return -0.0885862336f;
      }
    } else {
      if (x[7] < 3.23300147f) {
        if (x[8] < 37.3989525f) {
          return -0.0876938775f;
        } else {
          return 0.0845079869f;
        }
      } else {
        if (x[7] < 3.49697638f) {
          return 0.0810742751f;
        } else {
          return 0.0870094225f;
        }
      }
    }
  }
}
static inline float indra_ev_6_4(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.0843985155f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0839314237f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0856474712f;
        } else {
          return 0.083034806f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0801857933f;
        } else {
          return 0.0844287053f;
        }
      }
    }
  }
}
static inline float indra_ev_6_5(const float *x) {
  if (x[8] < 32.6142845f) {
    if (x[7] < 4.16863966f) {
      return -0.0816124678f;
    } else {
      if (x[11] < -5.0999999f) {
        if (x[9] < 0.692307711f) {
          return 0.0556107052f;
        } else {
          return 0.0822198018f;
        }
      } else {
        return -0.0806149542f;
      }
    }
  } else {
    if (x[8] < 33.7521477f) {
      if (x[7] < 4.16863966f) {
        return -0.0832549334f;
      } else {
        return 0.0804749653f;
      }
    } else {
      if (x[7] < 3.23300147f) {
        if (x[8] < 37.3989525f) {
          return -0.0817832574f;
        } else {
          return 0.0787227675f;
        }
      } else {
        if (x[7] < 3.65718746f) {
          return 0.0778789148f;
        } else {
          return 0.0813831314f;
        }
      }
    }
  }
}
static inline float indra_ev_6_6(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.079136692f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0788879395f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0810802206f;
        } else {
          return 0.0777581111f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0750850737f;
        } else {
          return 0.079183273f;
        }
      }
    }
  }
}
static inline float indra_ev_6_7(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.0769196153f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0765977129f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0786689296f;
        } else {
          return 0.075420998f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0728206113f;
        } else {
          return 0.07696338f;
        }
      }
    }
  }
}
static inline float indra_ev_6_8(const float *x) {
  if (x[8] < 32.6142845f) {
    if (x[0] < 34.2999992f) {
      return -0.0749248788f;
    } else {
      if (x[6] < 1.5f) {
        return 0.0735610723f;
      } else {
        return -0.0784138143f;
      }
    }
  } else {
    if (x[0] < 30.0f) {
      return -0.0746014267f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0767006725f;
        } else {
          return 0.0734807253f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0709025413f;
        } else {
          return 0.0749632195f;
        }
      }
    }
  }
}
static inline float indra_ev_6_9(const float *x) {
  if (x[0] < 30.6000004f) {
    if (x[6] < 25.6000004f) {
      return -0.0731239468f;
    } else {
      if (x[3] < 192.0f) {
        return -0.0737547502f;
      } else {
        if (x[2] < 993.700012f) {
          return 0.071909748f;
        } else {
          return -0.0603314526f;
        }
      }
    }
  } else {
    if (x[0] < 34.2999992f) {
      if (x[6] < 24.2000008f) {
        return -0.0743486807f;
      } else {
        if (x[6] < 24.7999992f) {
          return 0.053965833f;
        } else {
          return 0.0720355064f;
        }
      }
    } else {
      if (x[0] < 35.2000008f) {
        if (x[6] < 23.8999996f) {
          return 0.0659420341f;
        } else {
          return 0.0738172308f;
        }
      } else {
        return 0.0731625184f;
      }
    }
  }
}
static inline float indra_ev_6_10(const float *x) {
  if (x[0] < 30.6000004f) {
    if (x[6] < 25.6000004f) {
      return -0.0714929625f;
    } else {
      if (x[3] < 192.0f) {
        return -0.0718953088f;
      } else {
        if (x[4] < 235.0f) {
          return 0.0432656668f;
        } else {
          return 0.0682819039f;
        }
      }
    }
  } else {
    if (x[0] < 34.2999992f) {
      if (x[6] < 24.2000008f) {
        return -0.0725944489f;
      } else {
        if (x[6] < 25.6000004f) {
          return 0.0608841293f;
        } else {
          return 0.0710836425f;
        }
      }
    } else {
      if (x[0] < 35.2000008f) {
        if (x[2] < 1000.09998f) {
          return 0.0682706162f;
        } else {
          return 0.0583828464f;
        }
      } else {
        return 0.071525842f;
      }
    }
  }
}
static inline float indra_ev_6_11(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.0700126737f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0697619617f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0718412027f;
        } else {
          return 0.0685254261f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0654679462f;
        } else {
          return 0.0700404271f;
        }
      }
    }
  }
}
static inline float indra_ev_6_12(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.0686588734f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0684019551f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0703268573f;
        } else {
          return 0.0672196746f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0639818311f;
        } else {
          return 0.0686831772f;
        }
      }
    }
  }
}
static inline float indra_ev_6_13(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.0674203262f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0671168044f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0689561069f;
        } else {
          return 0.0658324286f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0627220497f;
        } else {
          return 0.0674432591f;
        }
      }
    }
  }
}
static inline float indra_ev_6_14(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.0662840158f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0659529567f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0676693767f;
        } else {
          return 0.0646099225f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0609058812f;
        } else {
          return 0.0663039312f;
        }
      }
    }
  }
}
static inline float indra_ev_6_15(const float *x) {
  if (x[8] < 32.2843628f) {
    return -0.065239273f;
  } else {
    if (x[0] < 30.0f) {
      return -0.0648294315f;
    } else {
      if (x[0] < 34.2999992f) {
        if (x[8] < 38.9874382f) {
          return -0.0665790886f;
        } else {
          return 0.0633895174f;
        }
      } else {
        if (x[0] < 35.2000008f) {
          return 0.0602049008f;
        } else {
          return 0.0652580187f;
        }
      }
    }
  }
}
static inline float indra_ev_head_6(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_6_0(x);
  raw += indra_ev_6_1(x);
  raw += indra_ev_6_2(x);
  raw += indra_ev_6_3(x);
  raw += indra_ev_6_4(x);
  raw += indra_ev_6_5(x);
  raw += indra_ev_6_6(x);
  raw += indra_ev_6_7(x);
  raw += indra_ev_6_8(x);
  raw += indra_ev_6_9(x);
  raw += indra_ev_6_10(x);
  raw += indra_ev_6_11(x);
  raw += indra_ev_6_12(x);
  raw += indra_ev_6_13(x);
  raw += indra_ev_6_14(x);
  raw += indra_ev_6_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_7_0(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0999933481f;
  } else {
    if (x[7] < 2.50801086f) {
      return -0.099701494f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0999935195f;
      } else {
        return -0.0896551758f;
      }
    }
  }
}
static inline float indra_ev_7_1(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0952358246f;
  } else {
    if (x[7] < 2.4607079f) {
      return -0.0949681774f;
    } else {
      if (x[6] < 8.39999962f) {
        return 0.0952058956f;
      } else {
        if (x[4] < 5.0f) {
          return 0.092870608f;
        } else {
          return -0.0840436444f;
        }
      }
    }
  }
}
static inline float indra_ev_7_2(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0911261737f;
  } else {
    if (x[7] < 2.4607079f) {
      return -0.0908798203f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0911269411f;
      } else {
        return -0.0853120238f;
      }
    }
  }
}
static inline float indra_ev_7_3(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0875438601f;
  } else {
    if (x[7] < 2.4607079f) {
      return -0.0873113275f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0875488147f;
      } else {
        return -0.0821177363f;
      }
    }
  }
}
static inline float indra_ev_7_4(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0843965039f;
  } else {
    if (x[0] < 22.8999996f) {
      return -0.0841664821f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0843483806f;
      } else {
        return -0.0821272358f;
      }
    }
  }
}
static inline float indra_ev_7_5(const float *x) {
  if (x[7] < 2.50801086f) {
    if (x[7] < 2.4607079f) {
      return -0.0816149563f;
    } else {
      if (x[10] < 0.5f) {
        return -0.0810788497f;
      } else {
        if (x[14] < -23.0f) {
          return 0.0830829293f;
        } else {
          return -0.0706587881f;
        }
      }
    }
  } else {
    if (x[6] < 8.39999962f) {
      if (x[2] < 1011.5f) {
        if (x[12] < -2.20000005f) {
          return -0.0704496354f;
        } else {
          return 0.0789893642f;
        }
      } else {
        return -0.0766491145f;
      }
    } else {
      return -0.0814979225f;
    }
  }
}
static inline float indra_ev_7_6(const float *x) {
  if (x[7] < 2.50801086f) {
    if (x[7] < 2.4607079f) {
      return -0.0791366324f;
    } else {
      if (x[11] < 1.29999995f) {
        return -0.0783291683f;
      } else {
        if (x[11] < 1.39999998f) {
          return 0.0820676535f;
        } else {
          return -0.0703483f;
        }
      }
    }
  } else {
    if (x[1] < 25.0369644f) {
      if (x[6] < 8.39999962f) {
        if (x[11] < 3.70000005f) {
          return 0.0766506717f;
        } else {
          return -0.0705706477f;
        }
      } else {
        if (x[9] < 1.83333337f) {
          return -0.0772425011f;
        } else {
          return 0.0796848536f;
        }
      }
    } else {
      return -0.0793124065f;
    }
  }
}
static inline float indra_ev_7_7(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0770887285f;
  } else {
    if (x[7] < 2.4607079f) {
      return -0.0767781138f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0770601854f;
      } else {
        return -0.0725765154f;
      }
    }
  }
}
static inline float indra_ev_7_8(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0750807375f;
  } else {
    if (x[0] < 22.8999996f) {
      return -0.0747151673f;
    } else {
      if (x[6] < 12.1999998f) {
        if (x[6] < 8.39999962f) {
          return 0.0749274939f;
        } else {
          return 0.0505948439f;
        }
      } else {
        return -0.0657902882f;
      }
    }
  }
}
static inline float indra_ev_7_9(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0732655972f;
  } else {
    if (x[7] < 2.4607079f) {
      return -0.0731527209f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0732397959f;
      } else {
        return -0.0719560459f;
      }
    }
  }
}
static inline float indra_ev_7_10(const float *x) {
  if (x[7] < 2.50801086f) {
    return -0.0714965388f;
  } else {
    if (x[1] < 25.0369644f) {
      if (x[6] < 8.39999962f) {
        if (x[2] < 1011.5f) {
          return 0.0692469105f;
        } else {
          return -0.0699561611f;
        }
      } else {
        if (x[4] < 5.0f) {
          return 0.0708118826f;
        } else {
          return -0.0696503371f;
        }
      }
    } else {
      return -0.071616441f;
    }
  }
}
static inline float indra_ev_7_11(const float *x) {
  if (x[5] < 5.0f) {
    if (x[7] < 2.50801086f) {
      return -0.0700007305f;
    } else {
      if (x[6] < 8.39999962f) {
        return -0.0797571167f;
      } else {
        return -0.0698862597f;
      }
    }
  } else {
    if (x[7] < 2.4607079f) {
      return -0.0700040683f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0701700822f;
      } else {
        return -0.0676778778f;
      }
    }
  }
}
static inline float indra_ev_7_12(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0688369125f;
  } else {
    if (x[0] < 22.8999996f) {
      return -0.0684400797f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0687573478f;
      } else {
        return -0.0685332641f;
      }
    }
  }
}
static inline float indra_ev_7_13(const float *x) {
  if (x[5] < 5.0f) {
    return -0.0675859675f;
  } else {
    if (x[0] < 22.8999996f) {
      return -0.0671987608f;
    } else {
      if (x[1] < 25.0369644f) {
        return 0.0674954578f;
      } else {
        return -0.0672047362f;
      }
    }
  }
}
static inline float indra_ev_7_14(const float *x) {
  if (x[7] < 2.50801086f) {
    if (x[7] < 2.4607079f) {
      return -0.0662766621f;
    } else {
      if (x[11] < 1.29999995f) {
        return -0.0664994568f;
      } else {
        if (x[11] < 1.39999998f) {
          return 0.0699394941f;
        } else {
          return -0.0596199632f;
        }
      }
    }
  } else {
    if (x[1] < 25.0369644f) {
      if (x[6] < 8.39999962f) {
        if (x[12] < -2.20000005f) {
          return -0.0598241873f;
        } else {
          return 0.0638091192f;
        }
      } else {
        if (x[9] < 1.83333337f) {
          return -0.0643989965f;
        } else {
          return 0.0650627241f;
        }
      }
    } else {
      return -0.0663356707f;
    }
  }
}
static inline float indra_ev_7_15(const float *x) {
  if (x[1] < 24.9766121f) {
    if (x[0] < 22.8999996f) {
      return -0.0651906207f;
    } else {
      if (x[2] < 1011.5f) {
        if (x[6] < 8.39999962f) {
          return 0.0623641871f;
        } else {
          return 0.00475369114f;
        }
      } else {
        return -0.0651487112f;
      }
    }
  } else {
    if (x[1] < 25.0369644f) {
      if (x[12] < -1.5f) {
        return 0.051742997f;
      } else {
        return -0.0644153655f;
      }
    } else {
      return -0.0652367398f;
    }
  }
}
static inline float indra_ev_head_7(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_7_0(x);
  raw += indra_ev_7_1(x);
  raw += indra_ev_7_2(x);
  raw += indra_ev_7_3(x);
  raw += indra_ev_7_4(x);
  raw += indra_ev_7_5(x);
  raw += indra_ev_7_6(x);
  raw += indra_ev_7_7(x);
  raw += indra_ev_7_8(x);
  raw += indra_ev_7_9(x);
  raw += indra_ev_7_10(x);
  raw += indra_ev_7_11(x);
  raw += indra_ev_7_12(x);
  raw += indra_ev_7_13(x);
  raw += indra_ev_7_14(x);
  raw += indra_ev_7_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_8_0(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0999935046f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0928571448f;
    } else {
      return 0.0999900401f;
    }
  }
}
static inline float indra_ev_8_1(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0952359661f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0889621824f;
    } else {
      return 0.0952320993f;
    }
  }
}
static inline float indra_ev_8_2(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0911263078f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0849681944f;
    } else {
      return 0.0911233798f;
    }
  }
}
static inline float indra_ev_8_3(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0875439793f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0818422064f;
    } else {
      return 0.0875389203f;
    }
  }
}
static inline float indra_ev_8_4(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0843966231f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0792334303f;
    } else {
      return 0.0843913332f;
    }
  }
}
static inline float indra_ev_8_5(const float *x) {
  if (x[4] < 257.0f) {
    return -0.081612885f;
  } else {
    if (x[9] < 0.315789461f) {
      if (x[6] < -0.600000024f) {
        if (x[15] < 2.00501156f) {
          return 0.0811126754f;
        } else {
          return -0.0742819533f;
        }
      } else {
        return -0.0797907338f;
      }
    } else {
      return -0.0815514848f;
    }
  }
}
static inline float indra_ev_8_6(const float *x) {
  if (x[4] < 253.0f) {
    return -0.0791349262f;
  } else {
    if (x[1] < 27.0849209f) {
      if (x[9] < 0.315789461f) {
        if (x[11] < -2.0f) {
          return -0.0755335763f;
        } else {
          return 0.0787755698f;
        }
      } else {
        return -0.0759395361f;
      }
    } else {
      return -0.0790928453f;
    }
  }
}
static inline float indra_ev_8_7(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0769481361f;
  } else {
    if (x[9] < 0.315789461f) {
      return 0.0769968554f;
    } else {
      return -0.0677139387f;
    }
  }
}
static inline float indra_ev_8_8(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0749521554f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0726165101f;
    } else {
      if (x[4] < 257.0f) {
        return 0.0791620016f;
      } else {
        return 0.074940607f;
      }
    }
  }
}
static inline float indra_ev_8_9(const float *x) {
  if (x[5] < 8.19999981f) {
    return -0.0731507689f;
  } else {
    if (x[9] < 0.255033553f) {
      if (x[14] < -149.0f) {
        return 0.0768387392f;
      } else {
        return 0.073081322f;
      }
    } else {
      return -0.0661525354f;
    }
  }
}
static inline float indra_ev_8_10(const float *x) {
  if (x[4] < 253.0f) {
    return -0.071496211f;
  } else {
    if (x[1] < 27.0849209f) {
      if (x[3] < 117.0f) {
        if (x[11] < -2.0f) {
          return -0.0674849376f;
        } else {
          return 0.0714232922f;
        }
      } else {
        return -0.0687331334f;
      }
    } else {
      return -0.0714421794f;
    }
  }
}
static inline float indra_ev_8_11(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0700465962f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0689663962f;
    } else {
      return 0.0703690052f;
    }
  }
}
static inline float indra_ev_8_12(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0686900467f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0674222708f;
    } else {
      return 0.0688544214f;
    }
  }
}
static inline float indra_ev_8_13(const float *x) {
  if (x[5] < 8.10000038f) {
    return -0.0674484894f;
  } else {
    if (x[4] < 253.0f) {
      return -0.0657540187f;
    } else {
      return 0.0677156821f;
    }
  }
}
static inline float indra_ev_8_14(const float *x) {
  if (x[4] < 253.0f) {
    return -0.0662828982f;
  } else {
    if (x[1] < 27.0849209f) {
      if (x[9] < 0.315789461f) {
        if (x[15] < 2.00501156f) {
          return 0.0660998821f;
        } else {
          return -0.0638342723f;
        }
      } else {
        return -0.0635492802f;
      }
    } else {
      return -0.0662311092f;
    }
  }
}
static inline float indra_ev_8_15(const float *x) {
  if (x[9] < 0.315789461f) {
    if (x[1] < 27.0849209f) {
      if (x[3] < 8.5f) {
        return -0.0649724156f;
      } else {
        if (x[11] < -2.0f) {
          return -0.0648590624f;
        } else {
          return 0.0620235614f;
        }
      }
    } else {
      return -0.0651413426f;
    }
  } else {
    return -0.0652370676f;
  }
}
static inline float indra_ev_head_8(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_8_0(x);
  raw += indra_ev_8_1(x);
  raw += indra_ev_8_2(x);
  raw += indra_ev_8_3(x);
  raw += indra_ev_8_4(x);
  raw += indra_ev_8_5(x);
  raw += indra_ev_8_6(x);
  raw += indra_ev_8_7(x);
  raw += indra_ev_8_8(x);
  raw += indra_ev_8_9(x);
  raw += indra_ev_8_10(x);
  raw += indra_ev_8_11(x);
  raw += indra_ev_8_12(x);
  raw += indra_ev_8_13(x);
  raw += indra_ev_8_14(x);
  raw += indra_ev_8_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_9_0(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0999921486f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.0983870998f;
      } else {
        return 0.057115119f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      return -0.0999494269f;
    } else {
      if (x[1] < 60.057518f) {
        return 0.0994916484f;
      } else {
        return -0.0996762887f;
      }
    }
  }
}
static inline float indra_ev_9_1(const float *x) {
  if (x[4] < 151.0f) {
    if (x[9] < 1.0545454f) {
      if (x[13] < 47.0999985f) {
        return -0.0952333733f;
      } else {
        if (x[9] < 1.01010096f) {
          return -0.0909685567f;
        } else {
          return 0.0628644451f;
        }
      }
    } else {
      if (x[5] < 1.60000002f) {
        return -0.0950401723f;
      } else {
        if (x[4] < 67.0f) {
          return -0.0483878069f;
        } else {
          return 0.0756894723f;
        }
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      return -0.0952117965f;
    } else {
      if (x[9] < 0.699999988f) {
        return -0.0957350209f;
      } else {
        if (x[7] < 0.160953715f) {
          return -0.08188802f;
        } else {
          return 0.0909137502f;
        }
      }
    }
  }
}
static inline float indra_ev_9_2(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0912783071f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.0909422562f;
      } else {
        return 0.0560236052f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      return -0.0910886973f;
    } else {
      if (x[1] < 60.057518f) {
        return 0.0909123197f;
      } else {
        return -0.0974487662f;
      }
    }
  }
}
static inline float indra_ev_9_3(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0876769498f;
    } else {
      if (x[8] < 36.2609138f) {
        return -0.0873989686f;
      } else {
        return 0.0481927805f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      return -0.087508589f;
    } else {
      if (x[1] < 60.057518f) {
        if (x[9] < 0.699999988f) {
          return -0.102128051f;
        } else {
          return 0.0877640247f;
        }
      } else {
        return -0.0930339321f;
      }
    }
  }
}
static inline float indra_ev_9_4(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.084514156f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.084162198f;
      } else {
        return 0.0521895364f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      return -0.084363237f;
    } else {
      if (x[1] < 60.057518f) {
        if (x[9] < 0.699999988f) {
          return -0.0969597846f;
        } else {
          return 0.0845958292f;
        }
      } else {
        return -0.0892161578f;
      }
    }
  }
}
static inline float indra_ev_9_5(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0817162395f;
    } else {
      if (x[8] < 36.2609138f) {
        return -0.0813486651f;
      } else {
        return 0.0466922931f;
      }
    }
  } else {
    if (x[7] < 0.24061197f) {
      if (x[6] < -8.60000038f) {
        if (x[7] < 0.160953715f) {
          return -0.0802762061f;
        } else {
          return 0.0517724529f;
        }
      } else {
        if (x[15] < -29.8592854f) {
          return 0.0757078752f;
        } else {
          return -0.0818281323f;
        }
      }
    } else {
      if (x[9] < 0.699999988f) {
        return -0.0852596834f;
      } else {
        if (x[6] < 22.5f) {
          return 0.0723172426f;
        } else {
          return 0.00863048807f;
        }
      }
    }
  }
}
static inline float indra_ev_9_6(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0792290866f;
    } else {
      if (x[8] < 36.2609138f) {
        return -0.0787617341f;
      } else {
        return 0.0448656417f;
      }
    }
  } else {
    if (x[1] < 60.057518f) {
      if (x[9] < 0.699999988f) {
        return -0.084176816f;
      } else {
        if (x[7] < 0.385538459f) {
          return 0.063962996f;
        } else {
          return 0.0767933652f;
        }
      }
    } else {
      if (x[7] < 0.24061197f) {
        return -0.0793631747f;
      } else {
        return -0.0848512501f;
      }
    }
  }
}
static inline float indra_ev_9_7(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0770037398f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.0765698478f;
      } else {
        return 0.0478710942f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      if (x[1] < 60.057518f) {
        return -0.0853452384f;
      } else {
        return -0.0781964585f;
      }
    } else {
      if (x[1] < 60.057518f) {
        if (x[9] < 0.699999988f) {
          return -0.0856353864f;
        } else {
          return 0.0774519071f;
        }
      } else {
        return -0.0834884718f;
      }
    }
  }
}
static inline float indra_ev_9_8(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0750014707f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.0744682103f;
      } else {
        return 0.043528948f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      return -0.0776125714f;
    } else {
      if (x[9] < 0.699999988f) {
        return -0.0811121091f;
      } else {
        if (x[6] < 22.2999992f) {
          return 0.0727667883f;
        } else {
          return 0.0472440049f;
        }
      }
    }
  }
}
static inline float indra_ev_9_9(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0731957704f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.0726119056f;
      } else {
        return 0.0424271077f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      if (x[1] < 60.057518f) {
        return -0.0799977183f;
      } else {
        return -0.0741251111f;
      }
    } else {
      if (x[1] < 60.057518f) {
        if (x[9] < 0.699999988f) {
          return -0.0798936784f;
        } else {
          return 0.0736353844f;
        }
      } else {
        return -0.0828415975f;
      }
    }
  }
}
static inline float indra_ev_9_10(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0715571418f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.0709297061f;
      } else {
        return 0.0409085564f;
      }
    }
  } else {
    if (x[1] < 60.057518f) {
      if (x[7] < 0.362180054f) {
        if (x[12] < -0.266666681f) {
          return 0.0390225425f;
        } else {
          return 0.0607491806f;
        }
      } else {
        if (x[12] < -1.39999998f) {
          return 0.0561937094f;
        } else {
          return 0.0687587559f;
        }
      }
    } else {
      if (x[7] < 0.24061197f) {
        return -0.0718935356f;
      } else {
        return -0.0765981898f;
      }
    }
  }
}
static inline float indra_ev_9_11(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0700685382f;
    } else {
      if (x[8] < 36.2609138f) {
        return -0.0694960952f;
      } else {
        return 0.0391245037f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      if (x[1] < 60.057518f) {
        return -0.0794451684f;
      } else {
        return -0.0708067045f;
      }
    } else {
      if (x[1] < 60.057518f) {
        if (x[9] < 0.699999988f) {
          return -0.0795081705f;
        } else {
          return 0.070518896f;
        }
      } else {
        return -0.0780089423f;
      }
    }
  }
}
static inline float indra_ev_9_12(const float *x) {
  if (x[4] < 151.0f) {
    if (x[9] < 1.07453418f) {
      if (x[9] < 1.01327431f) {
        return -0.0686377063f;
      } else {
        if (x[4] < 146.0f) {
          return -0.0679375827f;
        } else {
          return 0.0485090427f;
        }
      }
    } else {
      if (x[5] < 1.60000002f) {
        return -0.0687851831f;
      } else {
        if (x[4] < 58.0f) {
          return -0.039959304f;
        } else {
          return 0.052454371f;
        }
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      if (x[1] < 60.057518f) {
        if (x[9] < 0.708333313f) {
          return -0.0687341169f;
        } else {
          return -0.0759714618f;
        }
      } else {
        return -0.0691833943f;
      }
    } else {
      if (x[9] < 0.699999988f) {
        return -0.0692689642f;
      } else {
        if (x[1] < 60.057518f) {
          return 0.0681727007f;
        } else {
          return -0.0756378099f;
        }
      }
    }
  }
}
static inline float indra_ev_9_13(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0675168484f;
    } else {
      if (x[0] < 32.2000008f) {
        return -0.0671461821f;
      } else {
        return 0.0395465121f;
      }
    }
  } else {
    if (x[5] < 1.60000002f) {
      if (x[1] < 60.057518f) {
        return -0.0752181336f;
      } else {
        return -0.0680923462f;
      }
    } else {
      if (x[1] < 60.057518f) {
        if (x[9] < 0.699999988f) {
          return -0.075111419f;
        } else {
          return 0.0678798705f;
        }
      } else {
        return -0.074233152f;
      }
    }
  }
}
static inline float indra_ev_9_14(const float *x) {
  if (x[3] < 151.0f) {
    return -0.0663805827f;
  } else {
    if (x[1] < 60.057518f) {
      if (x[9] < 0.699999988f) {
        return -0.0707600266f;
      } else {
        if (x[7] < 0.385538459f) {
          return 0.0522287861f;
        } else {
          return 0.063859351f;
        }
      }
    } else {
      return -0.0679790974f;
    }
  }
}
static inline float indra_ev_9_15(const float *x) {
  if (x[3] < 151.0f) {
    if (x[3] < 149.0f) {
      return -0.0653200448f;
    } else {
      if (x[8] < 36.2609138f) {
        return -0.0648585111f;
      } else {
        return 0.0366869532f;
      }
    }
  } else {
    if (x[1] < 60.057518f) {
      if (x[9] < 0.699999988f) {
        return -0.0692436397f;
      } else {
        if (x[0] < 2.79999995f) {
          return 0.0512186252f;
        } else {
          return 0.0626706779f;
        }
      }
    } else {
      return -0.0667982101f;
    }
  }
}
static inline float indra_ev_head_9(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_9_0(x);
  raw += indra_ev_9_1(x);
  raw += indra_ev_9_2(x);
  raw += indra_ev_9_3(x);
  raw += indra_ev_9_4(x);
  raw += indra_ev_9_5(x);
  raw += indra_ev_9_6(x);
  raw += indra_ev_9_7(x);
  raw += indra_ev_9_8(x);
  raw += indra_ev_9_9(x);
  raw += indra_ev_9_10(x);
  raw += indra_ev_9_11(x);
  raw += indra_ev_9_12(x);
  raw += indra_ev_9_13(x);
  raw += indra_ev_9_14(x);
  raw += indra_ev_9_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_10_0(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0999932513f;
  } else {
    if (x[5] < 1.0f) {
      if (x[3] < 121.0f) {
        return -0.0990227982f;
      } else {
        if (x[2] < 1010.0f) {
          return -0.0981424153f;
        } else {
          return 0.0999935195f;
        }
      }
    } else {
      return -0.0997219607f;
    }
  }
}
static inline float indra_ev_10_1(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0952357277f;
  } else {
    if (x[5] < 1.0f) {
      if (x[2] < 1010.0f) {
        return -0.0943337604f;
      } else {
        if (x[4] < 121.0f) {
          return -0.0264607053f;
        } else {
          return 0.0948714837f;
        }
      }
    } else {
      return -0.0949901789f;
    }
  }
}
static inline float indra_ev_10_2(const float *x) {
  if (x[3] < 121.0f) {
    return -0.0911538079f;
  } else {
    if (x[5] < 1.0f) {
      if (x[2] < 1010.0f) {
        return -0.0909709781f;
      } else {
        if (x[14] < -26.0f) {
          return -0.0122075044f;
        } else {
          return 0.0824461058f;
        }
      }
    } else {
      return -0.0910935774f;
    }
  }
}
static inline float indra_ev_10_3(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0879332796f;
  } else {
    if (x[5] < 1.0f) {
      if (x[3] < 121.0f) {
        return -0.0897387266f;
      } else {
        if (x[2] < 1009.90002f) {
          return -0.0859670788f;
        } else {
          return 0.0878995582f;
        }
      }
    } else {
      return -0.087323837f;
    }
  }
}
static inline float indra_ev_10_4(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0847457051f;
  } else {
    if (x[5] < 1.0f) {
      if (x[3] < 121.0f) {
        return -0.0862983093f;
      } else {
        if (x[2] < 1010.0f) {
          return -0.0829335004f;
        } else {
          return 0.0847210363f;
        }
      }
    } else {
      return -0.0841860697f;
    }
  }
}
static inline float indra_ev_10_5(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0819216073f;
  } else {
    if (x[2] < 1010.0f) {
      return -0.0813442692f;
    } else {
      if (x[3] < 121.0f) {
        return -0.0828414187f;
      } else {
        if (x[7] < 1.46003675f) {
          return 0.0808798522f;
        } else {
          return 0.0466499291f;
        }
      }
    }
  }
}
static inline float indra_ev_10_6(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0794140324f;
  } else {
    if (x[3] < 121.0f) {
      return -0.079726845f;
    } else {
      if (x[0] < 23.5f) {
        if (x[6] < 18.5f) {
          return 0.0776571855f;
        } else {
          return -0.0737721547f;
        }
      } else {
        return -0.0782957077f;
      }
    }
  }
}
static inline float indra_ev_10_7(const float *x) {
  if (x[3] < 121.0f) {
    return -0.0768988058f;
  } else {
    if (x[5] < 1.0f) {
      if (x[13] < 0.100000001f) {
        return -0.0796975717f;
      } else {
        if (x[2] < 1010.0f) {
          return -0.0770677328f;
        } else {
          return 0.0726008341f;
        }
      }
    } else {
      return -0.0774347484f;
    }
  }
}
static inline float indra_ev_10_8(const float *x) {
  if (x[16] < 1.0f) {
    if (x[3] < 121.0f) {
      return -0.0748890862f;
    } else {
      if (x[5] < 1.0f) {
        if (x[2] < 1010.0f) {
          return -0.0746936053f;
        } else {
          return -0.0815900266f;
        }
      } else {
        return -0.0748437867f;
      }
    }
  } else {
    if (x[5] < 1.0f) {
      if (x[3] < 121.0f) {
        return -0.0760349482f;
      } else {
        if (x[2] < 1010.0f) {
          return -0.0758611783f;
        } else {
          return 0.075331822f;
        }
      }
    } else {
      return -0.0778898522f;
    }
  }
}
static inline float indra_ev_10_9(const float *x) {
  if (x[16] < 1.0f) {
    if (x[3] < 121.0f) {
      return -0.0730926991f;
    } else {
      if (x[5] < 1.0f) {
        if (x[2] < 1010.0f) {
          return -0.0729036853f;
        } else {
          return -0.0791101158f;
        }
      } else {
        return -0.0730492026f;
      }
    }
  } else {
    if (x[5] < 1.0f) {
      if (x[3] < 121.0f) {
        return -0.0740755871f;
      } else {
        if (x[2] < 1010.0f) {
          return -0.0737607107f;
        } else {
          return 0.0734910592f;
        }
      }
    } else {
      return -0.0758292302f;
    }
  }
}
static inline float indra_ev_10_10(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0718113855f;
  } else {
    if (x[2] < 1010.0f) {
      return -0.0721145198f;
    } else {
      if (x[3] < 121.0f) {
        return -0.0720393285f;
      } else {
        if (x[0] < 23.2999992f) {
          return 0.0707860664f;
        } else {
          return 0.0384415947f;
        }
      }
    }
  }
}
static inline float indra_ev_10_11(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0703015551f;
  } else {
    if (x[5] < 1.0f) {
      if (x[3] < 121.0f) {
        return -0.0706838295f;
      } else {
        if (x[2] < 1010.0f) {
          return -0.0702920333f;
        } else {
          return 0.0703351498f;
        }
      }
    } else {
      return -0.0735731572f;
    }
  }
}
static inline float indra_ev_10_12(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0689287409f;
  } else {
    if (x[5] < 1.0f) {
      if (x[2] < 1010.0f) {
        return -0.068682f;
      } else {
        if (x[4] < 121.0f) {
          return -0.0666931197f;
        } else {
          return 0.0686643943f;
        }
      }
    } else {
      return -0.0719702244f;
    }
  }
}
static inline float indra_ev_10_13(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0676679164f;
  } else {
    if (x[5] < 1.0f) {
      if (x[3] < 121.0f) {
        return -0.0689277276f;
      } else {
        if (x[2] < 1009.90002f) {
          return -0.0674530491f;
        } else {
          return 0.0676994249f;
        }
      }
    } else {
      return -0.0704462752f;
    }
  }
}
static inline float indra_ev_10_14(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0665146708f;
  } else {
    if (x[3] < 121.0f) {
      return -0.0666900501f;
    } else {
      if (x[0] < 24.1000004f) {
        if (x[6] < 20.8999996f) {
          return 0.0646721646f;
        } else {
          return -0.0525828674f;
        }
      } else {
        return -0.0649638698f;
      }
    }
  }
}
static inline float indra_ev_10_15(const float *x) {
  if (x[16] < 1.0f) {
    return -0.0654504523f;
  } else {
    if (x[2] < 1010.0f) {
      return -0.066352196f;
    } else {
      if (x[3] < 121.0f) {
        return -0.0659867823f;
      } else {
        if (x[0] < 22.8999996f) {
          return 0.0643612668f;
        } else {
          return 0.0354931802f;
        }
      }
    }
  }
}
static inline float indra_ev_head_10(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_10_0(x);
  raw += indra_ev_10_1(x);
  raw += indra_ev_10_2(x);
  raw += indra_ev_10_3(x);
  raw += indra_ev_10_4(x);
  raw += indra_ev_10_5(x);
  raw += indra_ev_10_6(x);
  raw += indra_ev_10_7(x);
  raw += indra_ev_10_8(x);
  raw += indra_ev_10_9(x);
  raw += indra_ev_10_10(x);
  raw += indra_ev_10_11(x);
  raw += indra_ev_10_12(x);
  raw += indra_ev_10_13(x);
  raw += indra_ev_10_14(x);
  raw += indra_ev_10_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
static inline float indra_ev_11_0(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[5] < 5.69999981f) {
      return -0.0972222239f;
    } else {
      return 0.0999856666f;
    }
  } else {
    return -0.0999934971f;
  }
}
static inline float indra_ev_11_1(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[5] < 5.69999981f) {
      return -0.0926301628f;
    } else {
      return 0.0952256843f;
    }
  } else {
    return -0.0952359661f;
  }
}
static inline float indra_ev_11_2(const float *x) {
  if (x[12] < -5.30000019f) {
    if (x[5] < 5.69999981f) {
      return -0.0863056108f;
    } else {
      return 0.0911214352f;
    }
  } else {
    return -0.0911268517f;
  }
}
static inline float indra_ev_11_3(const float *x) {
  if (x[5] < 6.0f) {
    return -0.087544553f;
  } else {
    if (x[6] < 5.4000001f) {
      return -0.0869267806f;
    } else {
      if (x[7] < 1.48049605f) {
        return 0.0875218287f;
      } else {
        return -0.0735394135f;
      }
    }
  }
}
static inline float indra_ev_11_4(const float *x) {
  if (x[5] < 6.0f) {
    return -0.0843971521f;
  } else {
    if (x[6] < 5.4000001f) {
      return -0.0838209093f;
    } else {
      if (x[10] < 1.5f) {
        return -0.0776020885f;
      } else {
        if (x[13] < 8.39999962f) {
          return 0.0843961909f;
        } else {
          return 0.0912206843f;
        }
      }
    }
  }
}
static inline float indra_ev_11_5(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[10] < 1.5f) {
      return -0.0793667287f;
    } else {
      if (x[3] < 57.0f) {
        return -0.0651401058f;
      } else {
        if (x[12] < -4.69999981f) {
          return 0.0815545097f;
        } else {
          return 0.0876052678f;
        }
      }
    }
  } else {
    return -0.0816137269f;
  }
}
static inline float indra_ev_11_6(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[10] < 1.5f) {
      return -0.076925531f;
    } else {
      if (x[3] < 80.0f) {
        return -0.0684817955f;
      } else {
        if (x[3] < 81.1999969f) {
          return 0.0844639689f;
        } else {
          return 0.0790667459f;
        }
      }
    }
  } else {
    return -0.079135783f;
  }
}
static inline float indra_ev_11_7(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[5] < 5.69999981f) {
      return -0.0762076601f;
    } else {
      if (x[5] < 6.19999981f) {
        return 0.0814393088f;
      } else {
        return 0.0768883154f;
      }
    }
  } else {
    return -0.0769186243f;
  }
}
static inline float indra_ev_11_8(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[5] < 5.69999981f) {
      return -0.0741027817f;
    } else {
      if (x[0] < 23.5f) {
        return 0.0748964474f;
      } else {
        return 0.0789623782f;
      }
    }
  } else {
    return -0.0749251544f;
  }
}
static inline float indra_ev_11_9(const float *x) {
  if (x[12] < -5.30000019f) {
    if (x[5] < 5.69999981f) {
      return -0.070720844f;
    } else {
      if (x[5] < 6.19999981f) {
        return 0.0765278265f;
      } else {
        return 0.0731040761f;
      }
    }
  } else {
    return -0.0731270984f;
  }
}
static inline float indra_ev_11_10(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[10] < 1.5f) {
      return -0.0698889494f;
    } else {
      if (x[3] < 57.0f) {
        return -0.057648886f;
      } else {
        if (x[12] < -4.69999981f) {
          return 0.0717431232f;
        } else {
          return 0.0789914951f;
        }
      }
    }
  } else {
    return -0.0714945048f;
  }
}
static inline float indra_ev_11_11(const float *x) {
  if (x[12] < -5.30000019f) {
    if (x[5] < 5.69999981f) {
      return -0.0683747381f;
    } else {
      if (x[9] < 0.315789461f) {
        return 0.0728529915f;
      } else {
        return 0.0699713752f;
      }
    }
  } else {
    return -0.0700124428f;
  }
}
static inline float indra_ev_11_12(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[5] < 5.69999981f) {
      return -0.068156451f;
    } else {
      if (x[12] < -5.19999981f) {
        if (x[9] < 0.315789461f) {
          return 0.0712418035f;
        } else {
          return 0.0686216801f;
        }
      } else {
        return 0.0787581727f;
      }
    }
  } else {
    return -0.068657361f;
  }
}
static inline float indra_ev_11_13(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[5] < 5.69999981f) {
      return -0.0668380633f;
    } else {
      if (x[12] < -5.19999981f) {
        if (x[9] < 0.315789461f) {
          return 0.069775492f;
        } else {
          return 0.0673849657f;
        }
      } else {
        return 0.0765761733f;
      }
    }
  } else {
    return -0.0674189702f;
  }
}
static inline float indra_ev_11_14(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[3] < 57.0f) {
      return -0.0632359684f;
    } else {
      if (x[0] < 20.5f) {
        return -0.0578151718f;
      } else {
        if (x[12] < -4.69999981f) {
          return 0.0664266124f;
        } else {
          return 0.0745612085f;
        }
      }
    }
  } else {
    return -0.066282846f;
  }
}
static inline float indra_ev_11_15(const float *x) {
  if (x[12] < -4.5999999f) {
    if (x[10] < 1.5f) {
      return -0.0642505139f;
    } else {
      if (x[12] < -4.69999981f) {
        return 0.0653632209f;
      } else {
        return 0.0728094503f;
      }
    }
  } else {
    return -0.0652380511f;
  }
}
static inline float indra_ev_head_11(const float *x) {
  float raw = 0.0f;
  raw += indra_ev_11_0(x);
  raw += indra_ev_11_1(x);
  raw += indra_ev_11_2(x);
  raw += indra_ev_11_3(x);
  raw += indra_ev_11_4(x);
  raw += indra_ev_11_5(x);
  raw += indra_ev_11_6(x);
  raw += indra_ev_11_7(x);
  raw += indra_ev_11_8(x);
  raw += indra_ev_11_9(x);
  raw += indra_ev_11_10(x);
  raw += indra_ev_11_11(x);
  raw += indra_ev_11_12(x);
  raw += indra_ev_11_13(x);
  raw += indra_ev_11_14(x);
  raw += indra_ev_11_15(x);
  return 1.0f / (1.0f + expf(-raw));
}
/* Returns 1 on success, 0 for null pointers or non-finite features.
 * Outputs are NAN on invalid sensor data. No heap allocation. */
static inline int indra_event_predict(const float *input, float *output) {
  if (!input || !output) return 0;
  for (int i = 0; i < 12; ++i) output[i] = NAN;
  float x[17];
  for (int i = 0; i < 17; ++i) {
    if (!isfinite(input[i])) return 0;
    x[i] = input[i];
  }
  output[0] = indra_ev_head_0(x);
  output[1] = indra_ev_head_1(x);
  output[2] = indra_ev_head_2(x);
  output[3] = indra_ev_head_3(x);
  output[4] = indra_ev_head_4(x);
  output[5] = indra_ev_head_5(x);
  output[6] = indra_ev_head_6(x);
  output[7] = indra_ev_head_7(x);
  output[8] = indra_ev_head_8(x);
  output[9] = indra_ev_head_9(x);
  output[10] = indra_ev_head_10(x);
  output[11] = indra_ev_head_11(x);
  return 1;
}
#endif
