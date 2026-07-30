using UnityEngine;
using Esri.ArcGISMapsSDK.Components;


public class FeatureInteractionManager : MonoBehaviour
{
    public Camera mainCamera;

    public ArcGISMapComponent map;

    public PopupManager popupManager;

    private void Update()
    {
        //FeatureHoverBehavior();
        FeatureClickBehavior();
    }

    private void CheckMapValidity()
    {
        if (map == null)
        {
            Debug.LogWarning("ArcGISMap object not found in scene.");
            return;
        }

        if (mainCamera == null)
        {
            Debug.LogWarning("ArcGISCamera not found in scene.");
            return;
        }
    }

  /*  private void FeatureHoverBehavior()
    {
        CheckMapValidity();

        Ray ray = mainCamera.ScreenPointToRay(Input.mousePosition);

        if(Physics.Raycast(ray,out RaycastHit hit))
        {
            FeatureInfo feature = hit.collider?.GetComponent<FeatureInfo>();
            {
                if(feature != null)
                {
                    Debug.Log($"Source: {feature.GetProperty("source")}");
                }
            }
        }
    } */
    private void FeatureClickBehavior()
    {
        CheckMapValidity();

        Ray ray = mainCamera.ScreenPointToRay(Input.mousePosition);

        if(Input.GetMouseButtonDown(0) && Physics.Raycast(ray, out RaycastHit hit))
        {
            FeatureInfo feature = hit.collider?.GetComponent<FeatureInfo>();
            
            if(feature != null)
            {
                Debug.Log($"popupManager = {popupManager}");
                Debug.Log($"feature = {feature}");
                popupManager.Show(feature);
            }
            
        }
    }

}
