import pandas as pd


def generate_ai_insights(df):

    insights=[]

    if df.empty:

        return ["No data loaded"]

    highest=df.groupby(

        "line_of_business"

    )["loss_ratio"].mean()

    worst=highest.idxmax()

    insights.append(

        f"{worst} has the highest loss ratio."

    )

    best=df.groupby(

        "line_of_business"

    )["gwp_usd"].sum()

    leader=best.idxmax()

    insights.append(

        f"{leader} generates the highest premium."

    )

    if df["combined_ratio"].mean()>1:

        insights.append(

            "Combined ratio exceeds 100%. Review pricing."

        )

    return insights