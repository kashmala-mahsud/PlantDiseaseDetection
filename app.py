import os
import base64
import streamlit as st
import tensorflow as tf
import numpy as np
import json
from PIL import Image

# ---------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Plant Disease Detector",
    page_icon="🌿",
    layout="centered"
)

# ---------------------------------------------------------------
# Background image helpers
# ---------------------------------------------------------------
# Apni khud ki image lagane ke liye, in me se kisi bhi naam se file rakh dein:
#   assets/background.jpg  |  assets/background.png  |  background.jpg  |  background.png
BG_CANDIDATES = [
    "assets/background.jpg",
    "assets/background.jpeg",
    "assets/background.png",
    "background.jpg",
    "background.jpeg",
    "background.png",
]


def file_to_data_uri(path):
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{encoded}"


def built_in_shadow_background():
    """Image na milne par ye shadowy leaf-style background use hoga."""
    svg = """
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 1000' preserveAspectRatio='xMidYMid slice'>
      <defs>
        <radialGradient id='bg' cx='50%' cy='40%' r='80%'>
          <stop offset='0%' stop-color='#1d4a2c'/>
          <stop offset='60%' stop-color='#0d2416'/>
          <stop offset='100%' stop-color='#040b07'/>
        </radialGradient>
        <filter id='blur'><feGaussianBlur stdDeviation='18'/></filter>
        <filter id='soft'><feGaussianBlur stdDeviation='6'/></filter>
      </defs>
      <rect width='1600' height='1000' fill='url(#bg)'/>
      <g filter='url(#blur)' opacity='0.55'>
        <path d='M-100 700 C 150 380, 450 330, 700 560 C 480 720, 220 820, -100 700 Z' fill='#2f8f4e'/>
        <path d='M900 -50 C 1150 120, 1350 80, 1700 260 C 1450 420, 1100 380, 900 -50 Z' fill='#3aa35d'/>
        <path d='M1100 650 C 1300 520, 1550 560, 1750 820 C 1500 1000, 1250 980, 1100 650 Z' fill='#25774190'/>
        <path d='M250 -80 C 420 60, 560 40, 760 180 C 560 300, 340 260, 250 -80 Z' fill='#1f6b3a'/>
      </g>
      <g filter='url(#soft)' opacity='0.35'>
        <path d='M120 820 C 260 640, 430 610, 600 720' stroke='#7ccf5a' stroke-width='3' fill='none'/>
        <path d='M1000 120 C 1150 220, 1300 210, 1450 300' stroke='#7ccf5a' stroke-width='3' fill='none'/>
        <path d='M1250 880 C 1350 800, 1450 790, 1550 840' stroke='#7ccf5a' stroke-width='3' fill='none'/>
      </g>
    </svg>
    """
    encoded = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{encoded}"


def get_background_uri():
    for path in BG_CANDIDATES:
        if os.path.exists(path):
            return file_to_data_uri(path)
    return built_in_shadow_background()


bg_uri = get_background_uri()

# ---------------------------------------------------------------
# Custom CSS (UI styling only - no effect on prediction logic)
# ---------------------------------------------------------------
st.markdown(
    f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{background: transparent;}}

    /* Shadowy full-screen background image */
    .stApp {{
        background-image:
            linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.80) 100%),
            url("{bg_uri}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}

    /* Dark vignette (shadow at the edges) */
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background: radial-gradient(ellipse at center,
                    rgba(0,0,0,0) 35%, rgba(0,0,0,0.75) 100%);
        z-index: 0;
    }}

    .block-container {{
        position: relative;
        z-index: 1;
        padding-top: 2rem;
        max-width: 780px;
    }}

    /* Glass hero header */
    .hero {{
        text-align: center;
        padding: 2.2rem 1.5rem;
        border-radius: 24px;
        background: rgba(10, 30, 18, 0.55);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(124, 207, 90, 0.35);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6),
                    0 0 40px rgba(63, 191, 107, 0.15);
        margin-bottom: 1.6rem;
    }}
    .hero h1 {{
        color: #ffffff;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: 0.5px;
        text-shadow: 0 4px 18px rgba(0, 0, 0, 0.8),
                     0 0 24px rgba(124, 207, 90, 0.45);
    }}
    .hero p {{
        color: #d7f7e0;
        margin: 0.7rem 0 0 0;
        font-size: 1.05rem;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.8);
    }}

    .section-title {{
        color: #b9f5c9;
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0.5rem 0 0.4rem 0;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.9);
    }}

    /* Glass uploader */
    [data-testid="stFileUploader"] section {{
        background: rgba(10, 30, 18, 0.55);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 2px dashed rgba(124, 207, 90, 0.8);
        border-radius: 18px;
        padding: 1.2rem;
    }}
    [data-testid="stFileUploader"] label p {{
        color: #e6ffee !important;
        font-weight: 600;
    }}

    /* Uploaded image with glow */
    [data-testid="stImage"] img {{
        border-radius: 20px;
        border: 3px solid rgba(124, 207, 90, 0.9);
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.75),
                    0 0 30px rgba(63, 191, 107, 0.35);
    }}
    [data-testid="stImage"] [data-testid="stCaptionContainer"] {{
        color: #bfe8cc;
        text-align: center;
    }}

    /* Detect button */
    .stButton > button {{
        width: 100%;
        background: linear-gradient(90deg, #2ea85a, #8be05f);
        color: #06200e;
        font-size: 1.1rem;
        font-weight: 800;
        border: none;
        border-radius: 16px;
        padding: 0.8rem 1rem;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.6),
                    0 0 22px rgba(63, 191, 107, 0.45);
        transition: all 0.2s ease-in-out;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.7),
                    0 0 34px rgba(139, 224, 95, 0.65);
        color: #06200e;
        border: none;
    }}

    /* Glass result card */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(10, 30, 18, 0.6);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(124, 207, 90, 0.55) !important;
        border-radius: 20px !important;
        padding: 0.7rem 0.9rem;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.65);
    }}

    .stApp h3 {{
        color: #ffffff;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.8);
    }}
    .stApp p, .stApp label, .stApp span {{
        color: #eafff0;
    }}

    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #2ea85a, #c2f56e);
        border-radius: 10px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------
# Load trained model
# ---------------------------------------------------------------
@st.cache_resource
def load_model():
    return tf.keras.models.load_model(
        "models/plant_disease_model.keras"
    )

model = load_model()

# Load class names
with open("models/class_names.json", "r") as file:
    class_names = json.load(file)

# ---------------------------------------------------------------
# Disease information for all 15 Custom CNN output classes
# Keys match the class_names.json labels produced by the notebook.
# ---------------------------------------------------------------
DISEASE_INFO = {
    "Pepper__bell___Bacterial_spot": {
        "type": "Bacterial disease",
        "description": "Bacterial spot affects pepper foliage and fruit. It can reduce plant vigor and marketable yield, especially in warm, wet conditions.",
        "symptoms": [
            "Small water-soaked spots that become dark brown or black.",
            "Yellow halos may appear around leaf spots.",
            "Severely affected leaves may yellow and drop.",
            "Raised or scabby spots can develop on fruit."
        ],
        "causes": [
            "Infection by Xanthomonas bacteria.",
            "Spread through infected seed or transplants, rain splash, tools, and handling wet plants.",
            "Warm weather and prolonged leaf wetness favor infection."
        ],
        "treatment": [
            "Remove badly affected plant debris; do not compost diseased material unless the composting process is reliably hot.",
            "Avoid overhead irrigation and do not handle plants while foliage is wet.",
            "Use only locally registered products labelled for bacterial spot on pepper; follow the label and local agricultural advice."
        ],
        "prevention": [
            "Use certified disease-free seed and healthy transplants.",
            "Rotate away from pepper and tomato crops where practical.",
            "Disinfect tools and keep workers and equipment from moving through wet crops.",
            "Use adequate spacing and improve airflow."
        ],
        "fertilizer": "No fertilizer cures bacterial spot. Use a soil-test-based, balanced pepper fertilizer; avoid excessive nitrogen, which can produce dense, tender growth."
    },
    "Pepper__bell___healthy": {
        "type": "Healthy class",
        "description": "The model classified the pepper leaf as belonging to the healthy pepper class. Continue routine crop care and monitoring.",
        "symptoms": [
            "Leaves are generally green and well formed.",
            "No clear disease pattern is identified in the uploaded image."
        ],
        "causes": [
            "This is a healthy reference class, not a disease."
        ],
        "treatment": [
            "No disease treatment is indicated by this prediction.",
            "Continue normal irrigation, scouting, and crop care."
        ],
        "prevention": [
            "Use clean tools and healthy seedlings.",
            "Maintain suitable spacing and avoid prolonged leaf wetness.",
            "Inspect plants regularly for new symptoms."
        ],
        "fertilizer": "Use a balanced fertilizer based on a soil test and the crop growth stage. Avoid over-fertilizing."
    },
    "Potato___Early_blight": {
        "type": "Fungal disease",
        "description": "Early blight is a common potato disease that mainly affects older foliage and can reduce leaf area and tuber yield.",
        "symptoms": [
            "Brown, dry leaf spots, often with concentric ring patterns.",
            "Yellowing around lesions, commonly beginning on older leaves.",
            "Lesions may enlarge and merge when disease pressure is high."
        ],
        "causes": [
            "Usually associated with the fungus Alternaria solani.",
            "Disease is favored by plant stress, warm conditions, and extended leaf wetness.",
            "Infected crop residue and volunteer potato plants can carry the pathogen."
        ],
        "treatment": [
            "Remove volunteer potatoes and manage infected crop residue after harvest.",
            "Maintain even irrigation and reduce plant stress.",
            "If needed, use a locally registered potato early-blight fungicide according to its label and resistance-management guidance."
        ],
        "prevention": [
            "Rotate crops and avoid planting potatoes repeatedly in the same field.",
            "Use healthy seed tubers and maintain balanced nutrition.",
            "Provide adequate spacing and avoid overhead irrigation late in the day."
        ],
        "fertilizer": "Maintain adequate, balanced nitrogen and potassium based on soil testing. Correct deficiencies, but do not use extra fertilizer as a disease cure."
    },
    "Potato___Late_blight": {
        "type": "Oomycete disease",
        "description": "Late blight is a potentially destructive potato disease that can spread rapidly in cool-to-mild, humid weather and may affect foliage and tubers.",
        "symptoms": [
            "Water-soaked, irregular dark lesions on leaves.",
            "White growth may appear at lesion edges in humid conditions, especially on leaf undersides.",
            "Dark stem lesions and firm, brownish tuber rot may occur."
        ],
        "causes": [
            "Caused by the oomycete Phytophthora infestans.",
            "Wind-blown spores and infected seed tubers or cull piles can spread the disease.",
            "Cool, wet weather and long periods of leaf wetness favor outbreaks."
        ],
        "treatment": [
            "Act quickly: isolate and remove infected plant material where practical.",
            "Do not save tubers from badly infected crops as seed.",
            "Contact a local agricultural extension service promptly; use only locally registered late-blight products exactly as labelled."
        ],
        "prevention": [
            "Plant certified disease-free seed tubers and destroy volunteer potatoes and cull piles.",
            "Monitor local late-blight alerts and inspect crops frequently in wet weather.",
            "Avoid overhead irrigation where possible and ensure good airflow."
        ],
        "fertilizer": "Use soil-test-based potato nutrition. Balanced potassium and appropriate nitrogen support crop growth, but fertilizer does not control late blight."
    },
    "Potato___healthy": {
        "type": "Healthy class",
        "description": "The model classified the potato leaf as belonging to the healthy potato class. Continue routine crop care and monitoring.",
        "symptoms": [
            "Foliage appears generally green and well formed.",
            "No clear disease pattern is identified in the uploaded image."
        ],
        "causes": [
            "This is a healthy reference class, not a disease."
        ],
        "treatment": [
            "No disease treatment is indicated by this prediction.",
            "Continue routine field scouting and irrigation management."
        ],
        "prevention": [
            "Use certified seed potatoes.",
            "Rotate crops and remove volunteer potato plants.",
            "Monitor foliage regularly, especially during humid weather."
        ],
        "fertilizer": "Base nitrogen, phosphorus, and potassium applications on soil testing and local potato recommendations. Avoid excess nitrogen."
    },
    "Tomato_Bacterial_spot": {
        "type": "Bacterial disease",
        "description": "Bacterial spot affects tomato leaves, stems, and fruit. It is more severe when foliage remains wet and can reduce fruit quality.",
        "symptoms": [
            "Small dark, water-soaked leaf spots that may develop yellow margins.",
            "Spots can merge, causing leaves to look scorched.",
            "Raised dark spots or scabby lesions may appear on fruit."
        ],
        "causes": [
            "Caused by Xanthomonas species.",
            "Spread by infected seed or transplants, splashing water, tools, and handling wet plants.",
            "Warm, humid conditions and leaf wetness favor spread."
        ],
        "treatment": [
            "Remove severely affected leaves and manage crop debris.",
            "Avoid overhead watering and work in the crop only when plants are dry.",
            "Ask local extension staff about registered bacterial-spot management options; follow product labels."
        ],
        "prevention": [
            "Start with disease-free seed and transplants.",
            "Rotate crops and avoid handling wet foliage.",
            "Disinfect tools and maintain good plant spacing."
        ],
        "fertilizer": "Use balanced tomato nutrition based on a soil test. Avoid excessive nitrogen; fertilizer cannot eliminate bacterial infection."
    },
    "Tomato_Early_blight": {
        "type": "Fungal disease",
        "description": "Tomato early blight commonly starts on older leaves and can cause premature defoliation, exposing fruit to sunscald.",
        "symptoms": [
            "Dark brown leaf spots with characteristic concentric rings.",
            "Yellowing around spots, often on lower, older leaves first.",
            "Stem lesions and dark, sunken spots near the stem end of fruit may occur."
        ],
        "causes": [
            "Usually caused by Alternaria solani.",
            "The pathogen can survive in infected crop debris and volunteer plants.",
            "Warm conditions, leaf wetness, and stressed plants favor disease."
        ],
        "treatment": [
            "Remove affected lower leaves when practical and dispose of diseased debris.",
            "Water at soil level and avoid prolonged leaf wetness.",
            "If necessary, use a locally registered tomato early-blight fungicide according to its label; rotate modes of action as directed."
        ],
        "prevention": [
            "Rotate crops and remove volunteer tomato and potato plants.",
            "Stake or trellis plants and provide airflow.",
            "Use mulch to reduce soil splash and maintain consistent watering."
        ],
        "fertilizer": "Provide balanced nutrition based on soil testing. Avoid nitrogen excess and correct potassium deficiencies if confirmed."
    },
    "Tomato_Late_blight": {
        "type": "Oomycete disease",
        "description": "Tomato late blight is a fast-moving disease that can damage leaves, stems, and fruit, particularly during cool, wet periods.",
        "symptoms": [
            "Irregular, water-soaked gray-green or brown leaf lesions.",
            "White fuzzy growth may develop at lesion margins in humid conditions.",
            "Dark stem lesions and firm brown fruit lesions may appear."
        ],
        "causes": [
            "Caused by Phytophthora infestans, an oomycete.",
            "Spores can spread by wind and water; infected potato crops may be a source.",
            "Cool, wet weather and prolonged leaf wetness favor outbreaks."
        ],
        "treatment": [
            "Remove and safely dispose of infected plant material where practical.",
            "Seek prompt local agricultural advice because outbreaks can progress quickly.",
            "Use only locally registered late-blight products for tomato and follow label directions."
        ],
        "prevention": [
            "Inspect crops frequently during cool, wet weather.",
            "Avoid overhead irrigation and improve spacing and airflow.",
            "Remove volunteer potatoes and tomatoes and manage infected crop debris."
        ],
        "fertilizer": "Use soil-test-based balanced nutrition. Fertilizer is not a treatment for late blight."
    },
    "Tomato_Leaf_Mold": {
        "type": "Fungal disease",
        "description": "Tomato leaf mold is primarily a foliage disease and is especially common in humid greenhouses or poorly ventilated growing areas.",
        "symptoms": [
            "Pale green or yellow patches on the upper leaf surface.",
            "Olive-green to grayish, velvety fungal growth on the underside of matching patches.",
            "Severe infection can cause leaves to curl, dry, and drop."
        ],
        "causes": [
            "Caused by Passalora fulva (also known by the older name Fulvia fulva).",
            "High humidity, condensation, and poor air circulation favor infection.",
            "The pathogen can persist on plant debris and contaminated structures."
        ],
        "treatment": [
            "Remove badly affected leaves and dispose of them away from the crop.",
            "Increase ventilation and reduce humidity and leaf wetness.",
            "Where necessary, consult local extension guidance for a registered product labelled for tomato leaf mold."
        ],
        "prevention": [
            "Provide good greenhouse ventilation and avoid overcrowding.",
            "Water at the base of plants and clean growing structures between crops.",
            "Choose resistant varieties when available."
        ],
        "fertilizer": "Maintain balanced tomato nutrition based on soil or growing-media testing. Avoid excess nitrogen and dense, overly lush growth."
    },
    "Tomato_Septoria_leaf_spot": {
        "type": "Fungal disease",
        "description": "Septoria leaf spot is a foliage disease of tomato that often begins on lower leaves and can cause substantial defoliation.",
        "symptoms": [
            "Numerous small, circular spots with dark margins and pale or gray centers.",
            "Tiny dark specks may be visible in the centers of mature lesions.",
            "Lower leaves often yellow and die as infection progresses."
        ],
        "causes": [
            "Caused by the fungus Septoria lycopersici.",
            "Spores spread by splashing water, tools, and movement through wet plants.",
            "Warm, wet conditions and infected crop debris support disease development."
        ],
        "treatment": [
            "Remove the most affected lower leaves without stripping the plant excessively.",
            "Avoid overhead watering and remove infected crop residue after harvest.",
            "If needed, use a locally registered Septoria management fungicide according to its label."
        ],
        "prevention": [
            "Rotate crops and control volunteer tomato plants and weeds in the nightshade family.",
            "Mulch to reduce soil splash and provide adequate plant spacing.",
            "Work with plants when foliage is dry."
        ],
        "fertilizer": "Use balanced fertilizer based on a soil test. Correct nutrient deficiencies, but do not expect fertilizer to cure leaf spot."
    },
    "Tomato_Spider_mites_Two_spotted_spider_mite": {
        "type": "Mite pest",
        "description": "Two-spotted spider mites are tiny sap-feeding pests, not a fungal or bacterial disease. They can multiply rapidly in hot, dry conditions.",
        "symptoms": [
            "Fine pale stippling or speckling on leaves.",
            "Leaves may bronze, yellow, dry, or drop when infestations are severe.",
            "Fine webbing may be visible on leaf undersides and stems."
        ],
        "causes": [
            "Feeding by two-spotted spider mites (Tetranychus urticae).",
            "Hot, dry conditions can favor rapid population growth.",
            "Dust and disruption of beneficial predatory mites can worsen outbreaks."
        ],
        "treatment": [
            "Check leaf undersides with a hand lens to confirm mites.",
            "Where suitable, wash foliage with a directed water spray and protect beneficial insects.",
            "If intervention is needed, use a locally registered miticide labelled for tomato and spider mites; follow the label and resistance-management directions."
        ],
        "prevention": [
            "Scout leaf undersides regularly, especially in hot, dry weather.",
            "Reduce dust and avoid unnecessary broad-spectrum insecticide use.",
            "Maintain adequate irrigation and conserve beneficial predatory mites."
        ],
        "fertilizer": "Maintain normal, balanced tomato nutrition. Excess nitrogen can encourage soft growth and does not control mites."
    },
    "Tomato__Target_Spot": {
        "type": "Fungal disease",
        "description": "Target spot is a fungal disease that affects tomato foliage and can also affect stems and fruit under favorable conditions.",
        "symptoms": [
            "Brown circular leaf lesions that may show concentric rings.",
            "Lesions can enlarge and merge, causing yellowing and leaf drop.",
            "Dark, sunken lesions may occur on stems or fruit."
        ],
        "causes": [
            "Commonly associated with Corynespora cassiicola.",
            "Warm, humid conditions and prolonged leaf wetness favor infection.",
            "Infected plant debris and splashing water can contribute to spread."
        ],
        "treatment": [
            "Remove badly affected leaves and manage crop debris.",
            "Improve airflow and avoid overhead irrigation.",
            "Consult local extension guidance for registered target-spot products; follow label directions and resistance-management advice."
        ],
        "prevention": [
            "Use crop rotation and remove volunteer host plants.",
            "Maintain good spacing, staking, and ventilation.",
            "Water at the soil line and avoid working among wet plants."
        ],
        "fertilizer": "Use soil-test-based balanced nutrition. Avoid excess nitrogen and correct deficiencies only when identified."
    },
    "Tomato__Tomato_mosaic_virus": {
        "type": "Viral disease",
        "description": "Tomato mosaic virus (ToMV) causes mosaic patterns and leaf distortion. There is no curative chemical treatment for an infected plant.",
        "symptoms": [
            "Light and dark green mosaic mottling on leaves.",
            "Leaves may be narrow, curled, or distorted.",
            "Plants may be stunted and fruit may ripen unevenly or show discoloration."
        ],
        "causes": [
            "Infection by Tomato mosaic virus.",
            "The virus spreads mechanically through contaminated hands, tools, clothing, and plant contact.",
            "Contaminated seed or plant debris can also be sources."
        ],
        "treatment": [
            "There is no cure for virus-infected plants; remove confirmed infected plants to limit spread.",
            "Do not handle healthy plants after touching suspected infected plants without cleaning hands and tools.",
            "Do not apply fungicides or fertilizers as a supposed cure for the virus."
        ],
        "prevention": [
            "Use certified virus-free seed and resistant varieties where available.",
            "Wash hands and disinfect tools between plants.",
            "Remove infected plants and crop debris; avoid tobacco use while handling plants because some tobacco products can carry related viruses."
        ],
        "fertilizer": "Fertilizer cannot cure a virus. Maintain balanced nutrition in healthy plants using soil-test results."
    },
    "Tomato__Tomato_YellowLeaf__Curl_Virus": {
        "type": "Viral disease",
        "description": "Tomato yellow leaf curl disease can severely restrict tomato growth and fruit production. It is transmitted mainly by whiteflies.",
        "symptoms": [
            "Upward curling and yellowing of leaf margins.",
            "Small, cupped leaves and shortened internodes.",
            "Stunted plants, flower drop, and reduced fruit set."
        ],
        "causes": [
            "Caused by Tomato yellow leaf curl virus (TYLCV) and related begomoviruses.",
            "Spread by infected whiteflies, especially Bemisia tabaci.",
            "Infected transplants and nearby host plants can help maintain the virus and vector."
        ],
        "treatment": [
            "There is no cure for virus-infected plants; remove confirmed infected plants where local guidance recommends it.",
            "Manage whiteflies using integrated pest management and locally approved methods.",
            "Avoid moving infested seedlings between fields."
        ],
        "prevention": [
            "Use healthy transplants and resistant varieties where suitable.",
            "Monitor whiteflies and manage weeds and volunteer host plants around production areas.",
            "Use insect-proof netting for nurseries where practical and follow local vector-management advice."
        ],
        "fertilizer": "Fertilizer does not cure TYLCV. Maintain balanced nutrition in healthy plants; avoid excess nitrogen."
    },
    "Tomato_healthy": {
        "type": "Healthy class",
        "description": "The model classified the tomato leaf as belonging to the healthy tomato class. Continue routine crop care and monitoring.",
        "symptoms": [
            "Leaves are generally green and well formed.",
            "No clear disease pattern is identified in the uploaded image."
        ],
        "causes": [
            "This is a healthy reference class, not a disease."
        ],
        "treatment": [
            "No disease treatment is indicated by this prediction.",
            "Continue routine crop scouting and appropriate irrigation."
        ],
        "prevention": [
            "Use healthy seedlings and clean tools.",
            "Maintain suitable spacing and airflow.",
            "Inspect leaves regularly, including their undersides."
        ],
        "fertilizer": "Use a balanced tomato fertilizer based on soil testing and crop stage. Avoid excessive nitrogen and maintain adequate potassium."
    }
}


def format_class_name(class_name):
    """Convert the notebook's raw class labels into clean display names."""
    display_names = {
        "Pepper__bell___Bacterial_spot": "Pepper Bell – Bacterial Spot",
        "Pepper__bell___healthy": "Pepper Bell – Healthy",
        "Potato___Early_blight": "Potato – Early Blight",
        "Potato___Late_blight": "Potato – Late Blight",
        "Potato___healthy": "Potato – Healthy",
        "Tomato_Bacterial_spot": "Tomato – Bacterial Spot",
        "Tomato_Early_blight": "Tomato – Early Blight",
        "Tomato_Late_blight": "Tomato – Late Blight",
        "Tomato_Leaf_Mold": "Tomato – Leaf Mold",
        "Tomato_Septoria_leaf_spot": "Tomato – Septoria Leaf Spot",
        "Tomato_Spider_mites_Two_spotted_spider_mite": "Tomato – Two-Spotted Spider Mites",
        "Tomato__Target_Spot": "Tomato – Target Spot",
        "Tomato__Tomato_mosaic_virus": "Tomato – Mosaic Virus",
        "Tomato__Tomato_YellowLeaf__Curl_Virus": "Tomato – Yellow Leaf Curl Virus",
        "Tomato_healthy": "Tomato – Healthy",
    }
    return display_names.get(class_name, class_name.replace("_", " ").replace("  ", " "))


def render_information_section(title, items):
    st.markdown(f"#### {title}")
    if isinstance(items, list):
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.write(items)


# ---------------------------------------------------------------
# Header
# ---------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🌿 Plant Disease Detection</h1>
        <p>Upload a plant leaf image to detect its disease using a trained CNN model.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------
# Image uploader
# ---------------------------------------------------------------
st.markdown('<div class="section-title">📤 Upload Image</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Choose a leaf image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    try:
        uploaded_image = Image.open(uploaded_file).convert("RGB")
    except Exception as error:
        st.error(f"Could not read this image. Please upload a valid JPG or PNG file. Details: {error}")
        st.stop()

    st.image(
        uploaded_image,
        caption="Uploaded Leaf Image",
        use_container_width=True
    )

    if st.button("🔍 Detect Disease"):
        with st.spinner("Analyzing leaf image..."):
            # Keep the original Custom CNN input pipeline unchanged:
            # 224x224 RGB image, raw 0-255 values. The saved CNN contains
            # its own Rescaling(1./255) layer.
            resized_image = uploaded_image.resize((224, 224))
            image_array = np.array(resized_image, dtype=np.float32)
            input_image = np.expand_dims(image_array, axis=0)

            prediction = model.predict(input_image, verbose=0)
            prediction_scores = prediction[0]

            if len(prediction_scores) != len(class_names):
                st.error(
                    "Model output count does not match models/class_names.json. "
                    "Please check that both files belong to the same trained model."
                )
                st.stop()

            predicted_index = int(np.argmax(prediction_scores))
            predicted_class = class_names[predicted_index]
            confidence = float(prediction_scores[predicted_index] * 100.0)

        display_name = format_class_name(predicted_class)
        info = DISEASE_INFO.get(predicted_class)

        st.success("Prediction completed!")

        with st.container(border=True):
            st.subheader("🌿 Plant Disease Detection Result")
            st.markdown("**Predicted class**")
            st.markdown(f"### {display_name}")
            st.write(f"**Confidence:** {confidence:.2f}%")
            st.progress(max(0.0, min(1.0, confidence / 100.0)))

            if info:
                st.caption(f"Category: {info['type']}")
                st.divider()
                st.markdown("### 1. Disease Description")
                st.write(info["description"])

                render_information_section("2. Symptoms", info["symptoms"])
                render_information_section("3. Causes", info["causes"])
                render_information_section("4. Treatment / Management", info["treatment"])
                render_information_section("5. Prevention Tips", info["prevention"])
                render_information_section("6. Fertilizer Guidance", info["fertilizer"])
            else:
                st.info(
                    "Detailed information for this class is not yet available. "
                    "Please check the class label and consult a local agricultural expert."
                )

        st.warning(
            "Important: This result is an AI prediction, not a confirmed laboratory diagnosis. "
            "Image quality, lighting, crop variety, and field conditions can affect predictions. "
            "Confirm uncertain cases with an agricultural extension officer or plant pathologist. "
            "Always follow local product labels and regulations before applying any crop treatment."
        )

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------
st.caption(
    "Plant Disease Detection • Custom CNN model • Educational decision-support tool"
)
