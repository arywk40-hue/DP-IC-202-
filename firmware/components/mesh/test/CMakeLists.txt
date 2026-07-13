idf_component_register(
    SRCS "test_mesh.c"
    INCLUDE_DIRS "../../include"
    REQUIRES mesh crypto unity
    EMBED_TXTFILES "test_mesh.c"
)