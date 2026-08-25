import streamlit as st
import numpy as np
import pandas as pd
import streamlit as st 


def intro():

    import streamlit as st

    
    st.title('Home page')

    st.write("")
    st.write("")
    st.write("")

    st.subheader("French Real Estate Project")

    st.write("")
    st.write("")
    st.write("")
    st.write("# Welcome 👋")
    st.write("")
    st.write("")
    st.subheader("Whether you are an individual, a real estate agency or simply a curious one, here you can observe the evolution of the financial value in France whether it is for buying a property, selling it, to help a client...")

    st.write("")
    st.write("")
    st.write("")

    st.markdown("Autor: SIVANANTHAN Sarankan")

    st.sidebar.success("Select an exploration mode above.")

    

@st.cache_data
def read_main_CSV(path):
        return pd.read_csv(path)

@st.cache_data
def sample(main_CSV , frac):
        return main_CSV.sample(frac = frac)


def count_rows(rows):
    return len(rows)

def get_month(dt):
    return dt.month

@st.cache_data
def apply_fct(col , _fct):
    return col.apply(_fct)

@st.cache_data
def merge(df1 , df2 , on , how):
    return pd.merge(df1 , df2 , on = on , how = how)

@st.cache_data
def process(df1 , df_dept):


    df1['date_mutation'] = pd.to_datetime(df1['date_mutation'])

    df1['mutation_month'] = apply_fct(df1['date_mutation'] , get_month)

    df1['code_departement'] = apply_fct(df1['code_departement'] , (lambda code_dept : str(code_dept)))

    df1['code_departement'] = apply_fct(df1['code_departement'] , (lambda code_dept : '0' + code_dept if (len(code_dept) == 1) else code_dept))

    df_dept['code_departement'] = apply_fct(df_dept['code_departement'] , (lambda code_dept : str(code_dept)))

    df1['type_local'] = df1['type_local'].fillna('Terrain')


    df1 = merge(df1 , df_dept , 'code_departement' , 'left')

    df1['surface_reelle_bati'] = df1['surface_reelle_bati'].fillna(0.0)

    df1['valeur_fonciere'] = df1.groupby(by = 'nom_departement')['valeur_fonciere'].transform(lambda x: x.fillna(x.mean()))

    df1['prix_m_carre'] = df1['valeur_fonciere'] / df1['surface_reelle_bati']



    df1['latitude'] = df1['latitude'].apply(lambda lat : float(lat))

    df1['longitude'] = df1['longitude'].apply(lambda long : float(long))

    return df1



def general_viz(datasets):
    import pandas as pd
    import streamlit as st 
    import plotly.express as px

    
    #st.markdown(f"# {list(page_names_to_funcs.keys())[1]}")

    st.title('General Visualization')

    year = st.sidebar.slider('Year' , 2019 , 2020)

    data = datasets[year]

    


    y = pd.DataFrame(data.groupby(by = 'nature_mutation').apply(count_rows).reset_index())

    y = y.rename(columns={0: "frequency"})

    st.write('Frequency of mutations - France ' + str(year))
 
    st.bar_chart(y , x = 'nature_mutation' , y = 'frequency')


    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")

    st.write('Mutation count by month')

    df_count_sale_by_month = pd.DataFrame(data.groupby(by = 'mutation_month').apply(count_rows).reset_index())

    df_count_sale_by_month = df_count_sale_by_month.rename(columns = {0 : 'frequency'})

    st.line_chart(df_count_sale_by_month , x = 'mutation_month' , y = 'frequency')




    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")


    df_count_by_local = pd.DataFrame(data.groupby(by = 'type_local').apply(count_rows).reset_index())

    df_count_by_local = df_count_by_local.rename(columns={0: 'frequency'})

    st.write('Locals count - France ' + str(year))

    fig = px.pie(df_count_by_local , names = 'type_local' , values = 'frequency' , hole = 0.3)

    st.plotly_chart(fig)


    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")

    st.write('Local mean price by Departement - France ' + str(year))

    df_mean_price_by_local = pd.DataFrame(data.groupby(by = ['nom_departement' , 'type_local'])['valeur_fonciere'].mean().reset_index())

    df_mean_price_by_local = df_mean_price_by_local.rename(columns={'valeur_fonciere': 'mean price'})

    fig = px.bar(df_mean_price_by_local , x = 'nom_departement' , y = 'mean price' , color = 'type_local')

    st.plotly_chart(fig)


    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")

    st.write('Square meter price by region - France ' + str(year))

    ##mask_maison_appartement = (data['type_local'] == 'Maison') | (data['type_local'] == 'Appartement')

    mask_prix_m_carre_diff_inf = data['prix_m_carre'] != np.inf

    df_price_by_region = pd.DataFrame(data[mask_prix_m_carre_diff_inf].groupby(by = 'nom_region')['prix_m_carre'].mean().reset_index())

    fig = px.bar(df_price_by_region , x = 'nom_region' , y = 'prix_m_carre')

    st.plotly_chart(fig)




    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")

    st.write('Mutations - France ' + str(year))
    mask_dom_tom = ~data['nom_departement'].isin(['Guadeloupe' , 'Guyane' , 'La Réunion' , 'Martinique'])
    fig = px.scatter(data[mask_dom_tom] , x = 'longitude' , y = 'latitude' ,
                    hover_data = ['type_local' , 'valeur_fonciere' , 'surface_reelle_bati' , 'surface_terrain'] ,
                    range_y = [data[mask_dom_tom]['latitude'].min() , data[mask_dom_tom]['latitude'].max()] ,
                    range_x = [data[mask_dom_tom]['longitude'].min() , data[mask_dom_tom]['longitude'].max()] , color = 'type_local')

    st.plotly_chart(fig)

def exploration(datasets):

    import streamlit as st
    import plotly.express as px

    st.title("Your exploration :mag_right:")

    year = st.sidebar.slider('Year' , 2019 , 2020)

    data = datasets[year]


    option_mutation = st.selectbox(
        'What type of mutation interests you',
        data['nature_mutation'].sort_values().unique())



    mask_mutation = data['nature_mutation'] == option_mutation



    option_local = st.selectbox(
        'What type of local interests you',
        data['type_local'].sort_values().unique())
            

    mask_local = data['type_local'] == option_local



    st.write(option_local + ' ' + option_mutation + ' by Month - France ' + str(year))


    fig = px.histogram(data[mask_mutation][mask_local] , x = 'mutation_month')

    st.plotly_chart(fig)




    option_region = st.multiselect(
        'What region interests you',
        data['nom_region'].sort_values().unique() , [] )



    mask_region = data['nom_region'].isin(option_region)

    if not option_region : st.error('Choose at least one region' , icon="🚨")

        

    option_departement = st.multiselect(
        'What departement interests you',
        data[mask_region]['nom_departement'].sort_values().unique() , data[mask_region]['nom_departement'].sort_values().unique())
        

    mask_departement = data['nom_departement'].isin(option_departement)


    mask_prix_m_carre_diff_inf = data['prix_m_carre'] != np.inf

    if(option_local != 'Terrain'):
        st.write('Square Meter Price by Departement')

        df_price_by_region = pd.DataFrame(data[mask_prix_m_carre_diff_inf][mask_departement][mask_local].groupby(by = 'nom_departement')['prix_m_carre'].mean().reset_index())

        fig = px.bar(df_price_by_region , x = 'nom_departement' , y = 'prix_m_carre')

        st.plotly_chart(fig)

    if (option_local in ('Appartement' , 'Maison')):
        option_nb_piece = st.selectbox(
        'How many rooms do you want' ,
        data[mask_region][mask_local]['nombre_pieces_principales'].sort_values().unique())

        mask_nb_piece = data['nombre_pieces_principales'] == option_nb_piece

        mask_local = mask_local & mask_nb_piece


    st.write('Price by Surface')
    if(option_local != 'Terrain'):
        df_price_by_ground = pd.DataFrame(data[mask_prix_m_carre_diff_inf][mask_departement][mask_local][['surface_reelle_bati' , 'valeur_fonciere' , 'nombre_pieces_principales' , 'nom_departement']])

        fig = px.scatter(df_price_by_ground , x = 'surface_reelle_bati' , y = 'valeur_fonciere' , color = 'nom_departement' , size = 'nombre_pieces_principales')
    
    if(option_local == 'Terrain'):
        df_price_by_ground = pd.DataFrame(data[mask_prix_m_carre_diff_inf][mask_departement][mask_local][['surface_terrain' , 'valeur_fonciere' , 'nom_departement']])
        st.write(df_price_by_ground)
        fig = px.scatter(df_price_by_ground , x = 'surface_terrain' , y = 'valeur_fonciere' , color = 'nom_departement')

    st.plotly_chart(fig)





    
    if (option_local in ('Terrain')):
        option_type_terrain = st.selectbox(
            'Wich type of field you want:' ,
            data[mask_region][mask_local]['nature_culture'].sort_values().unique())
        mask_type_terrain = data['nature_culture'] == option_type_terrain

        mask_local = mask_local & mask_type_terrain 



    map_view = st.radio("Choos your map view:" , ('Overview', 'Detailed View'))

    if not option_departement:
        loc2 = pd.DataFrame(data[mask_mutation][mask_local][mask_region][['latitude' , 'longitude']])
    if (len(option_departement) != 0) :
        loc2 = pd.DataFrame(data[mask_mutation][mask_local][mask_departement][['latitude' , 'longitude']])



    loc2 = loc2.dropna()



    if map_view == 'Overview' :
        st.map(loc2)
    
    if map_view == 'Detailed View':
        if (option_local != 'Terrain'):
             fig = px.scatter_mapbox(data[mask_mutation][mask_local][mask_departement], lat = 'latitude', lon = 'longitude' , color = 'nom_departement',
                    hover_name = "nom_commune",
                    hover_data = ['valeur_fonciere', 'type_local', 'nombre_pieces_principales', 'surface_reelle_bati'])
        else :
            fig = px.scatter_mapbox(data[mask_mutation][mask_local][mask_departement], lat = 'latitude', lon = 'longitude' , color = 'nom_departement',
                    hover_name = "nom_commune",
                    hover_data = ['valeur_fonciere', 'type_local', 'surface_terrain'])


        fig.update_layout(mapbox_style="open-street-map")
    
        st.plotly_chart(fig)

@st.cache_resource
def train_price_model(df_train):
    import numpy as np
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    feature_cols = ['type_local', 'surface_reelle_bati', 'nombre_pieces_principales', 'nom_departement']

    mask = (
        (df_train['nature_mutation'] == 'Vente')
        & df_train['type_local'].isin(['Maison', 'Appartement'])
        & (df_train['surface_reelle_bati'] > 8)
        & df_train['nombre_pieces_principales'].notna()
        & df_train['valeur_fonciere'].between(5000, 2_000_000)
    )
    data = df_train.loc[mask, feature_cols + ['valeur_fonciere']].dropna()

    X = data[feature_cols]
    y = np.log1p(data['valeur_fonciere'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    preprocessor = ColumnTransformer([
        ('categorical', OneHotEncoder(handle_unknown='ignore'), ['type_local', 'nom_departement']),
    ], remainder='passthrough')

    model = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=60, max_depth=10, min_samples_leaf=15, n_jobs=-1, random_state=42)),
    ])
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    r2 = r2_score(np.expm1(y_test), np.expm1(predictions))
    mae = mean_absolute_error(np.expm1(y_test), np.expm1(predictions))

    return model, r2, mae, sorted(data['nom_departement'].unique())


def prediction(df_train):
    import numpy as np
    import pandas as pd
    import streamlit as st

    st.title("Estimation - Prediction 🧠")

    st.write(
        "Estimate the sale price of a house or an apartment from its characteristics, "
        "using a Random Forest model trained on 2019 DVF sales data."
    )

    with st.spinner("Training the price estimation model..."):
        model, r2, mae, departements = train_price_model(df_train)

    st.caption(f"Model performance on held-out data — R²: {r2:.2f} · Mean absolute error: €{mae:,.0f}")

    col1, col2 = st.columns(2)

    with col1:
        type_local = st.selectbox("Property type", ["Appartement", "Maison"])
        default_dept = departements.index("Paris") if "Paris" in departements else 0
        departement = st.selectbox("Departement", departements, index=default_dept)

    with col2:
        surface = st.number_input("Living area (m²)", min_value=9, max_value=1000, value=60, step=1)
        rooms = st.number_input("Number of main rooms", min_value=1, max_value=20, value=3, step=1)

    to_predict = pd.DataFrame([{
        "type_local": type_local,
        "surface_reelle_bati": surface,
        "nombre_pieces_principales": rooms,
        "nom_departement": departement,
    }])

    predicted_price = np.expm1(model.predict(to_predict))[0]
    price_per_m2 = predicted_price / surface

    st.write("")

    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Estimated price", f"€{predicted_price:,.0f}")
    metric_col2.metric("Price per m²", f"€{price_per_m2:,.0f}")

    st.caption(
        "⚠️ Indicative estimate based on property type, surface, room count and department "
        "only — it does not account for exact location, condition or amenities, and is not "
        "a substitute for a professional appraisal."
    )




def main():
    df2019 = read_main_CSV("data/full_2019.csv")

    df_dept = read_main_CSV('data/departements-france.csv')

    df2019_sample_big = sample(df2019 , 0.3)

    df2019_sample_small = sample(df2019 , 0.05)

    df2020 = read_main_CSV("data/sampled_2020_by_dep.csv")

    df2020_sample_big = sample(df2020 , 0.3)

    df2020_sample_small = sample(df2020 , 0.05)

    

    df2019_sample_small = process(df2019_sample_small , df_dept)
    df2020_sample_small = process(df2020_sample_small , df_dept)
    df2019_sample_big = process(df2019_sample_big , df_dept)

    datasets = {2019 : df2019_sample_small,
                2020 : df2020_sample_small}



    page_names_to_funcs = {
            "Home page 🏠": intro,
            "General Visualizations 📊": general_viz,
            "Your exploration 🔎" : exploration,
            "Estimation - Prediction 🧠" : prediction,
    }

    demo_name = st.sidebar.selectbox("Exploration Type", page_names_to_funcs.keys())
    if demo_name == "Home page 🏠":
        page_names_to_funcs[demo_name]()
    elif demo_name == "Estimation - Prediction 🧠":
        page_names_to_funcs[demo_name](df2019_sample_big)
    else:
        page_names_to_funcs[demo_name](datasets)



if __name__ == "__main__":
    main()