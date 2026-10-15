#ifndef INDRA_CONSENSUS_POLICY_H
#define INDRA_CONSENSUS_POLICY_H
#include <stdint.h>
#include <stddef.h>
#include <math.h>
/* Input flags are derived by verified packet/registry/health handlers, never
 * accepted directly from an untrusted public request. Maximum origin + 6 peers. */
typedef struct {
 uint32_t physical_site_id,upstream_sensor_id,failure_domain;
 double weight,age_seconds,clock_uncertainty;
 uint8_t authenticated,physical,healthy,origin,agrees,valid_mask;
} indra_consensus_vote;
typedef struct {uint8_t corroborated,responding,agreeing,domains;double ratio;} indra_consensus_decision;
static inline int indra_consensus_policy(const indra_consensus_vote *votes,size_t n,uint8_t required,double maximum_age,indra_consensus_decision *out){
 if(!votes||!out||n>7||!required||required>63||!isfinite(maximum_age)||maximum_age<=0)return 0;
 out->corroborated=out->responding=out->agreeing=out->domains=0;out->ratio=NAN;
 double total=0,agree=0;int origin_agrees=0;uint32_t domains[7]={0};unsigned domain_count=0;
 for(size_t i=0;i<n;++i){const indra_consensus_vote *v=votes+i;
  if(!v->authenticated||!v->physical||!v->healthy||!isfinite(v->age_seconds)||v->age_seconds<0||v->age_seconds>maximum_age||!isfinite(v->clock_uncertainty)||v->clock_uncertainty<0||v->clock_uncertainty>30||!isfinite(v->weight)||v->weight<=0||(v->valid_mask&required)!=required)continue;
  for(size_t j=0;j<i;++j)if(votes[j].physical_site_id==v->physical_site_id||votes[j].upstream_sensor_id==v->upstream_sensor_id)return 0;
  ++out->responding;total+=v->weight;
  if(v->agrees){++out->agreeing;agree+=v->weight;if(v->origin)origin_agrees=1;if(v->failure_domain){int seen=0;for(unsigned j=0;j<domain_count;++j)seen|=domains[j]==v->failure_domain;if(!seen)domains[domain_count++]=v->failure_domain;}}
 }
 out->domains=domain_count;if(total>0)out->ratio=agree/total;
 out->corroborated=origin_agrees&&out->agreeing>=3&&domain_count>=2&&out->ratio>=2./3.;return 1;
}
#endif
