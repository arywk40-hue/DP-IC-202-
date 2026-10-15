#ifndef INDRA_PEER_PROTOCOL_H
#define INDRA_PEER_PROTOCOL_H
#include <math.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#if defined(ARDUINO)
#include <mbedtls/md.h>
#elif defined(INDRA_HOST_COMMONCRYPTO)
#include <CommonCrypto/CommonHMAC.h>
#elif defined(INDRA_HOST_OPENSSL)
#include <openssl/hmac.h>
#endif
#define INDRA_PEER_BODY_BYTES 64
#define INDRA_PEER_FRAME_BYTES 82
/* Network byte order; this is an application frame, not a LoRaWAN MAC frame. */
typedef struct {uint8_t body[64],tag[16],crc[2];} indra_peer_frame;
typedef char indra_peer_size_check[(sizeof(indra_peer_frame)==82)?1:-1];
typedef struct {
 uint8_t kind,flags,ttl,event_mask,valid_mask,fault_mask;
 uint32_t peer_id,origin_id,sequence,observed,deadline;
 uint64_t boot_id,query_id;uint16_t profile_id;
 float clock_uncertainty,raw[6],score[3];
} indra_peer_values;
static inline void indra_peer_u16(uint8_t *p,uint16_t v){p[0]=v>>8;p[1]=v;}
static inline void indra_peer_u32(uint8_t *p,uint32_t v){for(int i=3;i>=0;--i){p[i]=v;v>>=8;}}
static inline void indra_peer_u64(uint8_t *p,uint64_t v){for(int i=7;i>=0;--i){p[i]=v;v>>=8;}}
static inline uint16_t indra_peer_get16(const uint8_t *p){return ((uint16_t)p[0]<<8)|p[1];}
static inline uint32_t indra_peer_get32(const uint8_t *p){uint32_t v=0;for(int i=0;i<4;++i)v=(v<<8)|p[i];return v;}
static inline uint64_t indra_peer_get64(const uint8_t *p){uint64_t v=0;for(int i=0;i<8;++i)v=(v<<8)|p[i];return v;}
static inline uint16_t indra_peer_crc(const uint8_t *p,size_t n){
 uint16_t crc=0xffff;for(size_t i=0;i<n;++i){crc^=(uint16_t)p[i]<<8;for(int j=0;j<8;++j)crc=(crc&0x8000)?(uint16_t)((crc<<1)^0x1021):(uint16_t)(crc<<1);}return crc;
}
static inline int indra_peer_hmac(const uint8_t *key,size_t size,const uint8_t *body,uint8_t *tag){
 if(!key||!body||!tag||size<32||size>64)return 0;
 uint8_t digest[32];
#if defined(ARDUINO)
 const mbedtls_md_info_t *info=mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
 if(!info||mbedtls_md_hmac(info,key,size,body,64,digest)!=0)return 0;
#elif defined(INDRA_HOST_COMMONCRYPTO)
 CCHmac(kCCHmacAlgSHA256,key,size,body,64,digest);
#elif defined(INDRA_HOST_OPENSSL)
 unsigned n=32;if(!HMAC(EVP_sha256(),key,(int)size,body,64,digest,&n)||n!=32)return 0;
#else
 (void)digest;return 0; /* Fail closed without a real offline crypto backend. */
#endif
 memcpy(tag,digest,16);return 1;
}
static inline int indra_peer_pack(const indra_peer_values *v,const uint8_t *key,size_t key_size,indra_peer_frame *frame){
 if(!v||!frame||v->kind>5||(v->flags&~63)||v->ttl>1||v->event_mask>7||v->valid_mask>63||v->fault_mask>63||!isfinite(v->clock_uncertainty)||v->clock_uncertainty<0||v->clock_uncertainty>65.535f)return 0;
 if((v->kind==0||v->kind==2||v->kind==3)&&(v->event_mask&(v->flags&7)))return 0;
 uint8_t *b=frame->body;memset(frame,0,sizeof(*frame));b[0]='I';b[1]='H';b[2]=1;b[3]=v->kind;b[4]=v->flags;b[5]=v->ttl;
 indra_peer_u32(b+6,v->peer_id);indra_peer_u32(b+10,v->origin_id);indra_peer_u64(b+14,v->boot_id);indra_peer_u64(b+22,v->query_id);
 indra_peer_u32(b+30,v->sequence);indra_peer_u32(b+34,v->observed);indra_peer_u32(b+38,v->deadline);indra_peer_u16(b+42,v->profile_id);
 b[44]=v->event_mask;b[45]=v->valid_mask;indra_peer_u16(b+46,(uint16_t)fmin(65535.,ceil((double)v->clock_uncertainty*1000.)));
 const double lo[6]={-60,0,300,0,0,0},hi[6]={85,100,1100,5000,5000,100},scale[6]={100,100,10,1,1,100};
 for(int i=0;i<6;++i){int16_t value=-32768;if(v->valid_mask&(1u<<i)){if(!isfinite(v->raw[i])||v->raw[i]<lo[i]||v->raw[i]>hi[i])return 0;double x=v->raw[i]*scale[i];value=(int16_t)(x>=0?floor(x+.5):ceil(x-.5));}indra_peer_u16(b+48+2*i,(uint16_t)value);}
 b[60]=v->fault_mask;for(int i=0;i<3;++i){if(isnan(v->score[i]))b[61+i]=255;else{if(!isfinite(v->score[i])||v->score[i]<0||v->score[i]>1)return 0;b[61+i]=(uint8_t)floor((double)v->score[i]*254+.5);}}
 if(!indra_peer_hmac(key,key_size,b,frame->tag))return 0;
 indra_peer_u16(frame->crc,indra_peer_crc((const uint8_t *)frame,80));return 1;
}
static inline int indra_peer_unpack(const indra_peer_frame *frame,const uint8_t *key,size_t key_size,indra_peer_values *v){
 if(!frame||!v||indra_peer_get16(frame->crc)!=indra_peer_crc((const uint8_t *)frame,80))return 0;
 uint8_t tag[16],difference=0;if(!indra_peer_hmac(key,key_size,frame->body,tag))return 0;
 for(int i=0;i<16;++i)difference|=tag[i]^frame->tag[i];if(difference)return 0;
 const uint8_t *b=frame->body;if(b[0]!='I'||b[1]!='H'||b[2]!=1||b[3]>5||(b[4]&~63)||b[5]>1||b[44]>7||b[45]>63||b[60]>63)return 0;
 v->kind=b[3];v->flags=b[4];v->ttl=b[5];v->peer_id=indra_peer_get32(b+6);v->origin_id=indra_peer_get32(b+10);
 v->boot_id=indra_peer_get64(b+14);v->query_id=indra_peer_get64(b+22);v->sequence=indra_peer_get32(b+30);v->observed=indra_peer_get32(b+34);v->deadline=indra_peer_get32(b+38);v->profile_id=indra_peer_get16(b+42);
 v->event_mask=b[44];v->valid_mask=b[45];v->clock_uncertainty=indra_peer_get16(b+46)/1000.f;v->fault_mask=b[60];
 if((v->kind==0||v->kind==2||v->kind==3)&&(v->event_mask&(v->flags&7)))return 0;
 const float scale[6]={100,100,10,1,1,100},lo[6]={-60,0,300,0,0,0},hi[6]={85,100,1100,5000,5000,100};
 for(int i=0;i<6;++i){int16_t n=(int16_t)indra_peer_get16(b+48+2*i);v->raw[i]=n==-32768?NAN:n/scale[i];if((v->valid_mask&(1u<<i))&&(!isfinite(v->raw[i])||v->raw[i]<lo[i]||v->raw[i]>hi[i]))return 0;}
 for(int i=0;i<3;++i)v->score[i]=b[61+i]==255?NAN:b[61+i]/254.f;return 1;
}
#endif
