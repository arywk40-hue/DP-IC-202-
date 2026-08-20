idf_component_register(
    SRCS "test_crypto.c"
    INCLUDE_DIRS "../../include"
    REQUIRES crypto unity
    EMBED_TXTFILES "test_crypto.c"
)