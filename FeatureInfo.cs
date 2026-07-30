using System.Collections.Generic;
using UnityEngine;
using Newtonsoft.Json.Linq;
using Esri.GameEngine.Geometry;
//INSTRUCTIONS
/* JObject -- can be anything with a "{}" as its value
   JProperty -- can be any key such as "tpye", "geometry", "coordinates", "name", etc
   JValue -- a value pair that is represented by a string or that actual values in an array ("Point" value for geometry type "type" key)
   JArray -- a value pair that's represented by an array (coordinates key/value have as their value a JArray of JValues

   JObject --> Feature
        JProperty --> featureType
                JValue --> "Feauture
        JProperty --> "Geometry"
                JObject (value pair of JProperty "geometry")
                        JProperty --> type
                                JValue --> "Point"/"Line"/"Polygon"
                        JProperty --> coordinates
                                JArray (value pair of coordinates)
                                        JValue --> coordinate
                                        JValue --> coordinate
*/

public class FeatureInfo : MonoBehaviour
{
    public ArcGISGeometry MapGeometry { get; private set; } //Stores the ArcGIS geom created from the geoJSON feature.
    public JObject feature; //stores the entire feature as a JObject
    public string FeatureType  //gets the feature type value of the feature
    {
        get
        {
            if (feature == null)
            {
                return null;
            }

            if (feature["type"] == null)
            {
                return null;
            }

            return feature["type"].ToString();
        }
    }

    public JObject Geometry  //gets the geometry JObject (contains geometry tpye and coordinates)
    {
        get
        {
            if (feature == null)
            {
                return null;
            }

            if (feature["geometry"] == null)
            {
                return null;
            }

            return feature["geometry"] as JObject;
        }
    }

    public JObject Properties  //gets the properties of the feature
    {
        get
        {
            if (feature == null)
            {
                return null;
            }

            if (feature["properties"] == null)
            {
                return null;
            }

            return feature["properties"] as JObject;
        }
    }
    public string GeometryType   //gets the geometry type value of the feature
    {
        get
        {
            if (Geometry == null)
            {
                return null;
            }

            if (Geometry["type"] == null)
            {
                return null;
            }

            return Geometry["type"].ToString();
        }
    }
    public JToken Coordinates   //Gets the coordinate key of the feature
    {
        get
        {
            if (Geometry == null)
            {
                return null;
            }

            if (Geometry["coordinates"] == null)
            {
                return null;
            }

            return Geometry["coordinates"];
        }
    }

    public double Latitude  //Gets the latitude value (for points) 
    {
        get
        {
            return Coordinates[0].Value<double>();
        }
    }

    public double Longitude //Gets the longitude value (for points) 
    {
        get
        {
            return Coordinates[1].Value<double>();
        }
    }

    private double GetLatitude(JToken coordinate) // GetLatitude/GetLongitude are used to retrieve lat/lon iterating through coord pairs.
    {
        return coordinate[0].Value<double>();
    }

    private double GetLongitude(JToken coordinate)
    {
        return coordinate[1].Value<double>();
    }
    
    public bool HasProperty(string key)         //Checks whether or not a feature has a particular property
    {
        if(!Properties.ContainsKey(key))
        {
            return false;
        }
        else
        {
            return true;
        }
    }
    public JToken GetProperty(string key)    //gets the property key
    {
        if (!HasProperty(key))
        {
            return null;
        }
        return Properties[key];
    }
    public IEnumerable<JProperty> GetAllProperties()  //gets all properties of the feature
    {
        if (Properties == null)
        {
            yield break;
        }

        foreach (JProperty property in Properties.Properties())
        {
            yield return property;
        }
    }

    public IEnumerable<(double latitude, double longitude)> GetCoordinates() //returns every coordinate for the feature as a sequence of coord pairs
    {
        if(Coordinates == null)
        {
            yield break;
        }

        switch (GeometryType)
        {
            case "Point":
                yield return (Latitude, Longitude);
                break;

            case "Linestring":
                foreach(JToken coordinate in Coordinates)
                {
                    yield return (GetLatitude(coordinate), GetLongitude(coordinate));
                }
                break;

            case "Polygon":
                foreach (JToken coordinate in Coordinates[0])
                {
                    yield return (GetLatitude(coordinate), GetLongitude(coordinate));
                }
                break;

        }

    }

    private ArcGISGeometry CreatePoint()   //Creates a point from properties Latitude/Longitude
    {
        if(Coordinates == null)
        {
            Debug.LogWarning("Point geometry has no coordinates.");
            return null;
        }

        double latitude = Latitude;
        double longitude = Longitude;

        return new ArcGISPoint(latitude, longitude, 0.0, ArcGISSpatialReference.WGS84());
    }

    private ArcGISGeometry CreatePolyline() //creates linestring of type ArcGISGemometry. Lines are a series of corrdinates hence foreach
    {
        if (Coordinates == null)
        {
            Debug.LogWarning("Polyline geometry has no coordinates");
            return null;
        }

        ArcGISPolylineBuilder builder = new ArcGISPolylineBuilder(ArcGISSpatialReference.WGS84());

        foreach (JToken coordinate in Coordinates)
        {
            builder.AddPoint(new ArcGISPoint(GetLatitude(coordinate), GetLongitude(coordinate), 0.0, ArcGISSpatialReference.WGS84()));
        }

        return builder.ToGeometry();
    }

    private ArcGISGeometry CreatePolygon() //Creates a polygon. GeoJSON has one more level of nesting for polygons so Coordinates[0] instead of Corrdinates
    {
        if (Coordinates == null)
        {
            Debug.LogWarning("Polygon geometry has no coordinates");
            return null;
        }

        ArcGISPolygonBuilder builder = new ArcGISPolygonBuilder(ArcGISSpatialReference.WGS84());

        foreach(JToken coordinate in Coordinates[0])
        {        
            builder.AddPoint(new ArcGISPoint(GetLatitude(coordinate), GetLongitude(coordinate), 0.0, ArcGISSpatialReference.WGS84()));
        }
        return builder.ToGeometry();
    }

    private ArcGISGeometry CreateGeometry()  //creates a geometry based on the GeometryType retruned.
    {
        switch (GeometryType)
        {
            case "Point":
                return CreatePoint();

            case "LineString":
                return CreatePolyline();

            case "Polygon":
                return CreatePolygon();

            default:
                Debug.LogWarning($"Unsupported geometry type: {GeometryType}");
                return null;
        }
    }
    public void Initialize(JObject feature) //initializing the geometry from the geoJSON feature. Used in GeoJSONLoader to initialize the feature data for the appropriate game object.
    {
        this.feature = feature;

        if (this.feature == null)
        {
            Debug.LogWarning("Cannot initialize FeatureInfo: feature is null.");
            return;
        }

        if (Geometry == null)
        {
            Debug.LogWarning("Feature has no geometry.");
            return;
        }

        MapGeometry = CreateGeometry();

        if (MapGeometry == null)
        {
            Debug.LogWarning($"Failed to create ArcGIS geometry for type: {GeometryType}");
            return;
        }

        Debug.Log($"Feature initialized successfully. Type: {FeatureType}, Geometry: {GeometryType}, Coordinates: [{Latitude}, {Longitude}]"); //for now only have Points.
    }
}

