# Diagrama de flujo del sistema (Mermaid)

A continuación, el diagrama de flujo de punta a punta del chatbot. Puede visualizarse directamente en GitHub o con cualquier visor compatible con Mermaid.

```mermaid
flowchart TD
    %% Entrada
    A[Usuario] --> B[ChatbotService.process_message]

    %% Clasificación y complejidad
    B --> C[IntentClassifier]
    C -->|Gemini disponible| C1[Gemini: classify_intent]
    C -->|Fallback| C2[Regex patterns]
    C1 --> D[determine_query_complexity]
    C2 --> D

    %% Contexto desde BD
    B --> E[_get_comprehensive_context]
    E --> F[DatabaseService]
    F --> G[(Supabase)]

    %% Tablas principales
    G --> G1[[Productos\n(product_id, product_name, availability)]]
    G --> G2[[Pedidos\n(order_id, customer_name, status)]]
    G --> G3[[Info_empresa\n(topic, info)]]

    %% Contexto específico de la consulta
    E --> H{query_specific}
    H --> H1[Productos en stock / bajo demanda / búsqueda]
    H --> H2[Pedidos por estado / cliente / ID]
    H --> H3[Políticas relevantes (40 topics)]

    %% Generación de respuesta
    B --> I{Gemini disponible?}
    I -->|Sí| J[_build_rich_context_prompt]
    J --> K[GeminiService.generate_response\n(prompt neutral)]
    K --> L{¿Respuesta genérica o inválida?}
    L -->|Sí| M[_generate_direct_db_response\n(usa datos de BD)]
    L -->|No| N[Respuesta AI]

    I -->|No| M

    %% Limpieza y salida
    M --> O[_clean_output]
    N --> O
    O --> P[Guardar en memoria simple]
    P --> Q[Respuesta al usuario]

    %% Leyenda
    classDef db fill:#e3f2fd,stroke:#64b5f6,color:#0d47a1
    classDef svc fill:#ede7f6,stroke:#9575cd,color:#311b92
    classDef ai fill:#fff3e0,stroke:#ffb74d,color:#e65100

    class F,G,G1,G2,G3 db
    class B,E,M,O,P,Q svc
    class C,C1,K,N ai
```

