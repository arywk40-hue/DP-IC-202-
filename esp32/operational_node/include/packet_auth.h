#pragma once
#include <Arduino.h>
#include <new>
#include <mbedtls/md.h>
#include <mbedtls/base64.h>

// Sign the EXACT UTF-8 payload bytes. No JSON float/canonicalization assumption.
static inline bool indra_signed_packet(const String& node,const String& nonce,const String& sent,
 const uint8_t* key,size_t key_len,const String& payload,String& result){
  if(!key||key_len<32||node.length()==0||node.length()>64||nonce.length()<16||nonce.length()>128||sent.length()<20||sent.length()>35||payload.length()>16000)return false;
  String message=node+"\n"+nonce+"\n"+sent+"\n"+payload;
  uint8_t digest[32];const auto* info=mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  if(!info||mbedtls_md_hmac(info,key,key_len,reinterpret_cast<const uint8_t*>(message.c_str()),message.length(),digest))return false;
  String hex;hex.reserve(64);char byte[3];for(int i=0;i<32;++i){snprintf(byte,sizeof(byte),"%02x",digest[i]);hex+=byte;}
  size_t size=4*((payload.length()+2)/3)+1,written=0;uint8_t* encoded=new(std::nothrow) uint8_t[size];
  if(!encoded)return false;
  if(mbedtls_base64_encode(encoded,size,&written,reinterpret_cast<const uint8_t*>(payload.c_str()),payload.length())){delete[] encoded;return false;}
  encoded[written]=0;
  result="{\"protocol\":\"indra_hmac_v1\",\"node_id\":\""+node+"\",\"nonce\":\""+nonce+"\",\"sent_at_utc\":\""+sent+"\",\"payload_base64\":\""+String(reinterpret_cast<char*>(encoded))+"\",\"signature_hex\":\""+hex+"\"}";
  delete[] encoded;return true;
}
