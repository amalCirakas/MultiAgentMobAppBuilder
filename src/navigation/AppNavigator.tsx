import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import { HomeScreen } from "../screens/HomeScreen";
import { ModulePlaceholderScreen } from "../screens/ModulePlaceholderScreen";
import { RootStackParamList } from "../types/navigation";

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator(): JSX.Element {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: "HospitalOS" }} />
        <Stack.Screen
          name="PatientRegistration"
          options={{ title: "Patients" }}
          children={() => <ModulePlaceholderScreen title="Patient Module" moduleKey="patients" />}
        />
        <Stack.Screen
          name="AppointmentScheduling"
          options={{ title: "Appointments" }}
          children={() => <ModulePlaceholderScreen title="Appointment Module" moduleKey="appointments" />}
        />
        <Stack.Screen
          name="VitalsEntry"
          options={{ title: "Vitals" }}
          children={() => <ModulePlaceholderScreen title="Vitals Module" moduleKey="vitals" />}
        />
        <Stack.Screen
          name="AdmissionManagement"
          options={{ title: "Admission" }}
          children={() => <ModulePlaceholderScreen title="Admission Module" moduleKey="admission" />}
        />
        <Stack.Screen
          name="Billing"
          options={{ title: "Billing" }}
          children={() => <ModulePlaceholderScreen title="Billing Module" moduleKey="billing" />}
        />
        <Stack.Screen
          name="Pharmacy"
          options={{ title: "Pharmacy" }}
          children={() => <ModulePlaceholderScreen title="Pharmacy Module" moduleKey="pharmacy" />}
        />
        <Stack.Screen
          name="LabOrders"
          options={{ title: "Labs" }}
          children={() => <ModulePlaceholderScreen title="Lab Module" moduleKey="labs" />}
        />
        <Stack.Screen
          name="AuthAndRole"
          options={{ title: "Auth and Roles" }}
          children={() => <ModulePlaceholderScreen title="Auth Module" moduleKey="auth" />}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
