"""Aplicacion Streamlit placeholder para el proyecto."""

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="SICOES RAG", layout="wide")
    st.title("Sistema RAG para convocatorias del SICOES")
    st.caption("Scaffold inicial del proyecto de monografia.")

    st.info(
        "La interfaz conversacional y el pipeline RAG completo se implementaran en fases "
        "posteriores. Este modulo solo define la estructura base del proyecto."
    )

    st.subheader("Componentes previstos")
    st.write(
        [
            "Extraccion y almacenamiento de datos crudos",
            "Limpieza y transformacion orientada a RAG",
            "Embeddings y almacenamiento en PostgreSQL + pgvector",
            "Busqueda keyword con SQL, busqueda semantica y RAG",
            "Evaluacion comparativa y documentacion academica",
        ]
    )


if __name__ == "__main__":
    main()
