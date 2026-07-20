using UnityEngine;
using System.IO;
using Esri.GameEngine.Geometry;
using Esri.ArcGISMapsSDK.Components;
using Newtonsoft.Json.Linq;
using System.Collections;
using Esri.HPFramework;
using System.Collections.Generic;
using UnityEngine.Timeline;
using UnityEngine.LowLevelPhysics;

public class GeoJSONLoader : MonoBehaviour
{
    public string[] geoJSONFilePaths = { @"C:\Users\theim\PycharmProjects\pythonProject4\locations.geojson", 
        @"C:\Users\theim\PycharmProjects\pythonProject4\s2underground_posts.geojson", 
        @"C:\Users\theim\PycharmProjects\pythonProject4\article_events.geojson" }; //file paths for geojsons
    public GameObject pointPrefab;   //declaring GameObject variable. Each feature in the geojson file will be created

    //private float defaultAltitude = 5.0f; // Default is set to 1000ft. Want to ensure the features are visible for testing.
    public ArcGISMapComponent map;          //ArcGISMpaComponent object

    public List<FeatureInfo> loadedFeatures = new List<FeatureInfo>();

    void Start()
    {
        GameObject mapGameObject = GameObject.Find("ArcGISMap");

        if (mapGameObject != null)
        {
            map = mapGameObject.GetComponent<ArcGISMapComponent>();

            if (map != null)
            {
                StartCoroutine(WaitForMapInitialization());
            }
            else
            {
                Debug.LogError("ArcGISMapComponent not found on the GameObject.");
            }
        }
        else
        {
            Debug.LogError("GameObject 'ArcGISMap' not found in the scene.");
        }
    }

    //Funtion to make sure the map is active in the game object hierarchy before doing anything else. Once this is confirmed
    //LoadGeoJSON() is called
    IEnumerator WaitForMapInitialization()
    {
        while (!map.gameObject.activeInHierarchy)
        {
            yield return null; //Wait for the next frame
        }

        foreach(string filepath in geoJSONFilePaths) 
        {
            LoadGeoJSON(filepath);
        }
       
    }

    // Function below to load the geojson and parse its geospatial data
    private void LoadGeoJSON(string filepath)
    {
        string geoJSONText = File.ReadAllText(filepath); //create an object to read text from the input file path defined in variables section.
        JObject geoJSONData = JObject.Parse(geoJSONText); //JObject and the Parse() fucntion are from the Newtonsoft Json library. in this case I'm parsing the 
                                                          // text from the file path and storing that in a JObject called geoJSONDa
      
        foreach (JObject featureObject in geoJSONData["features"])
        {
            CreateFeatureVisual(featureObject);
        }
    }

    // Function to create the game object
    private void CreateFeatureVisual(JObject feature)
    {
        GameObject marker = pointPrefab ? Instantiate(pointPrefab) : GameObject.CreatePrimitive(PrimitiveType.Sphere);
        marker.transform.localScale = Vector3.one * 25000f;
        Collider col = marker.GetComponent<Collider>();
        col.transform.localScale = Vector3.one * 35000f;

        marker.transform.SetParent(map.transform, true);

        FeatureInfo info = marker.AddComponent<FeatureInfo>();

        info.Initialize(feature);

        loadedFeatures.Add(info);

        StartCoroutine(InitializeMarkerLocation(marker, info.Latitude, info.Longitude));
    }

    private IEnumerator InitializeMarkerLocation(GameObject marker, double latitude, double longitude)
    {
        while (!map.gameObject.activeInHierarchy)
        {
            yield return null; 
        }

        ArcGISLocationComponent locationComponent = marker.AddComponent<ArcGISLocationComponent>();
        locationComponent.Position = new ArcGISPoint(longitude, latitude, 0, ArcGISSpatialReference.WGS84());     
    }
}
