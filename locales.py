# -*- coding: utf-8 -*-


def decode_literal_dict(d):
    return {k: v.decode('utf8') for k, v in d.items()}

translations = {
    "en": {
        "courses": decode_literal_dict({
            "NUMBER_OF_LESSONS": "Number of lessons",
            "DESIGNED_FOR": "Designed for",
            "TIME_TO_COMPLETE": "Time to complete",
            "TOPIC": "Topic",
            "DEVELOPED_WITH_RAISE_THE_BAR": "Developed in collaboration with Raise the Bar",
            "GROW_YOUR_BRAIN": "Grow your brain.",
            "VIEW RELATED_MATERIALS_FROM_RESOURCE_LIBRARY": "View related materials from our resource library",
            "VIEW_RELATED_RESOURCES": "View Related Resources"
        }),
        "lessons": decode_literal_dict({
            "NEXT_LESSON": "Next lesson",
            "NEXT": "Next",
            "NEXT_TOPIC": "Next topic",
            "FINISH_TOPIC": "Finish topic",
            "LIKE": "Like",
            "LIKED": "Like",
            "PRINT_THIS_PAGE": "Print this page",
            "COMMENTS_AND_DISCUSSION": "Comments and discussion",
            "ENTER_COMMENT": "Enter a comment",
            "WRITE_COMMENT": "Write a comment",
            "REPLY": "Reply",
            "VIDEO_TRANSCRIPTION": "Video Transcription",
            "RELATED_RESOURCES": "Related Resources"
        }),
        "books": decode_literal_dict({
            "NUMBER_OF_PAGES": "Number of pages",
            "DESIGNED_FOR": "Designed for",
            "TIME_TO_COMPLETE": "Time to complete",
            "CHAPTER": "Chapter"
        }),
        "pages": decode_literal_dict({
            "NEXT_PAGE": "Next page",
            "NEXT": "Next",
            "NEXT_CHAPTER": "Next chapter",
            "FINISH_CHAPTER": "Finish chapter",
            "LIKE": "Like",
            "LIKED": "Like",
            "PRINT_THIS_PAGE": "Print this page",
            "COMMENTS_AND_DISCUSSION": "Comments and discussion",
            "ENTER_COMMENT": "Enter a comment",
            "WRITE_COMMENT": "Write a comment",
            "REPLY": "Reply",
            "VIDEO_TRANSCRIPTION": "Video Transcription",
            "RELATED_RESOURCES": "Related Resources"
        })
    },

    "es": {
        "courses": decode_literal_dict({
            "NUMBER_OF_LESSONS": "Número de Sesiones",
            "DESIGNED_FOR": "Diseñadas para",
            "TIME_TO_COMPLETE": "Tiempo para completar",
            "TOPIC": "Tema",
            "DEVELOPED_WITH_RAISE_THE_BAR": "Elaborado en colaboración con Raise The Bar",
            "GROW_YOUR_BRAIN": "Desarrolla Tu Mente.",
            "VIEW RELATED_MATERIALS_FROM_RESOURCE_LIBRARY": "Consultar material relacionado de nuestra biblioteca de recursos",
            "VIEW_RELATED_RESOURCES": "Consultar material relacionado"
        }),
        "lessons": decode_literal_dict({
            "NEXT_LESSON": "Próxima lección",
            "NEXT": "Próxima",
            "NEXT_TOPIC": "Siguiente tema",
            "FINISH_TOPIC": "Finalizar tema",
            "LIKE": "Me gusta",
            "LIKED": "Me ha gustado",
            "PRINT_THIS_PAGE": "Imprimir esta página",
            "COMMENTS_AND_DISCUSSION": "comentarios y discusión",
            "ENTER_COMMENT": "introducir un comentario",
            "WRITE_COMMENT": "Escribe un comentario",
            "REPLY": "Responder",
            "VIDEO_TRANSCRIPTION": "Transcripción del vídeo",
            "RELATED_RESOURCES": "Recursos relacionados"
        })
    }
}
