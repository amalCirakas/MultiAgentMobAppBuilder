import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { ModuleCard } from "../components/ModuleCard";
import { RootStackParamList } from "../types/navigation";

type Props = NativeStackScreenProps<RootStackParamList, "Home">;

const MODULE_LINKS: Array<{ route: keyof RootStackParamList; title: string; subtitle: string }> = [
  { route: "PatientRegistration", title: "Patients", subtitle: "Registration and profile management" },
  { route: "AppointmentScheduling", title: "Appointments", subtitle: "Scheduling and rescheduling" },
  { route: "VitalsEntry", title: "Vitals", subtitle: "Vitals and nursing notes" },
  { route: "AdmissionManagement", title: "Admission", subtitle: "Admission, discharge, bed flow" },
  { route: "Billing", title: "Billing", subtitle: "Invoice and payment state" },
  { route: "Pharmacy", title: "Pharmacy", subtitle: "Prescription and dispensing" },
  { route: "LabOrders", title: "Labs", subtitle: "Orders and results" },
  { route: "AuthAndRole", title: "Auth and Roles", subtitle: "Login and permissions" },
];

export function HomeScreen({ navigation }: Props): JSX.Element {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.heading}>Hospital Management</Text>
      <Text style={styles.subheading}>Choose a module to work on or test.</Text>
      <View style={styles.list}>
        {MODULE_LINKS.map((moduleLink) => (
          <ModuleCard
            key={moduleLink.route}
            title={moduleLink.title}
            subtitle={moduleLink.subtitle}
            onPress={() => navigation.navigate(moduleLink.route)}
          />
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    backgroundColor: "#f8fafc",
  },
  heading: {
    fontSize: 24,
    fontWeight: "800",
    color: "#0f172a",
  },
  subheading: {
    marginTop: 8,
    marginBottom: 16,
    fontSize: 14,
    color: "#334155",
  },
  list: {
    marginTop: 4,
  },
});
